import secrets
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.embedder import Embedder
from app.odoo_client import OdooClient
from app.search import run_search
from app.state import State
from app.store import Store
from app.sync import sync_once

_ctx = {}


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
    _ctx["embedder"] = Embedder(settings.embed_model)
    _ctx["store"] = Store(settings.chroma_path)
    _ctx["state"] = State(f"{settings.chroma_path}/state.db")
    _ctx["odoo"] = OdooClient(
        settings.odoo_url, settings.odoo_db,
        settings.odoo_user, settings.odoo_password,
    )
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


@app.post("/search")
def search_endpoint(req: SearchReq, x_search_token: str = Header(default="")):
    if not settings.search_token or not secrets.compare_digest(
        x_search_token, settings.search_token
    ):
        raise HTTPException(status_code=401, detail="invalid token")
    return run_search(
        req.query, req.ai_mode, _ctx["embedder"], _ctx["store"],
        req.top_k or settings.top_k,
        settings.groq_api_key, settings.groq_model,
    )


@app.get("/healthz")
def healthz():
    return {"status": "ok", "indexed": _ctx["store"].count()}
