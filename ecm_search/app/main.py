import secrets
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.embedder import Embedder
from app.odoo_client import OdooClient
from app.reranker import Reranker
from app.search import run_search
from app.state import State
from app.store import Store
from app.sync import sync_once

_ctx = {}

# Versão do esquema de indexação. Bumpar quando build_embedding_text mudar —
# força wipe + reindex no próximo restart, mesmo sem trocar o modelo.
_INDEX_SCHEMA = "3"


def _run_sync():
    try:
        count = sync_once(
            _ctx["odoo"], _ctx["embedder"], _ctx["store"],
            _ctx["state"], settings.reconcile_every,
        )
        print(f"[sync] indexed {count} docs")
    except Exception as exc:  # keep the scheduler alive on transient errors
        print(f"[sync] error: {exc}")


@asynccontextmanager
async def lifespan(_app):
    odoo = OdooClient(
        settings.odoo_url, settings.odoo_db,
        settings.odoo_user, settings.odoo_password,
    )
    store = Store(settings.chroma_path)
    state = State(f"{settings.chroma_path}/state.db")

    # Modelo de embedding: parâmetro do Odoo sobrepõe o env. A chave de índice
    # combina modelo + versão do esquema — se qualquer um mudou desde a última
    # indexação, zera o índice e reindexa do zero nos próximos ciclos de sync
    # (vetores de modelos/esquemas distintos não são comparáveis).
    embed_model = odoo.get_config_param(
        "afr_ecm.search.embed_model", settings.embed_model
    )
    index_key = f"{embed_model}|schema{_INDEX_SCHEMA}"
    if state.get_embed_model() != index_key:
        print(f"[startup] índice desatualizado ({index_key}); reindexando do zero")
        store.reset()
        state.set_checkpoint("1970-01-01 00:00:00")
        state.set_embed_model(index_key)

    _ctx["embedder"] = Embedder(embed_model)
    _ctx["reranker"] = Reranker(settings.rerank_model)
    _ctx["store"] = store
    _ctx["state"] = state
    _ctx["odoo"] = odoo
    scheduler = BackgroundScheduler()
    scheduler.add_job(_run_sync, "interval", minutes=settings.sync_interval_min)
    scheduler.start()
    _ctx["scheduler"] = scheduler
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)


class SearchReq(BaseModel):
    query: str
    ai_mode: bool = False
    top_k: int | None = None
    min_score: float | None = None
    rel_cutoff: float | None = None
    groq_model: str | None = None


@app.post("/search")
def search_endpoint(req: SearchReq, x_search_token: str = Header(default="")):
    if not settings.search_token or not secrets.compare_digest(
        x_search_token, settings.search_token
    ):
        raise HTTPException(status_code=401, detail="invalid token")
    return run_search(
        req.query, req.ai_mode, _ctx["embedder"], _ctx["store"], _ctx["reranker"],
        req.top_k or settings.top_k,
        settings.groq_api_key, req.groq_model or settings.groq_model,
        min_score=req.min_score if req.min_score is not None else 0.0,
        rel_cutoff=req.rel_cutoff if req.rel_cutoff is not None else 0.0,
    )


@app.get("/healthz")
def healthz():
    return {"status": "ok", "indexed": _ctx["store"].count()}
