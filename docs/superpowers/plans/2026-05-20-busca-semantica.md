# Busca Semântica — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a semantic document search for the ECM — natural-language queries return documents ranked by semantic similarity.

**Architecture:** A new standalone microservice (`ecm-search`) pulls OCR'd documents from Odoo via JSON-RPC (cron), embeds them with sentence-transformers, and stores vectors in ChromaDB. Search runs through an authenticated afr_ecm proxy controller (applies ACL) and is consumed by a search UI in the ecm_desktop Electron app.

**Tech Stack:** Python 3.11, FastAPI, ChromaDB, sentence-transformers, Groq, APScheduler, pytest (microservice); Odoo 16 controller (afr_ecm); Next.js/React (ecm_desktop).

---

## Repo / commit rules

This feature spans three git repos. Per project `CLAUDE.md`, commit from inside each repo with the `git-commit-push` agent, staging specific paths only (never `git add -A`):

- **Monorepo** `/home/afonso/docker/odoo_engenapp` — `ecm_search/`, `docker-compose.yml`, `docs/`.
- **Submodule** `addons/afr_ecm` — controller + data.
- **Submodule** `ecm_desktop` — search UI.

Commit steps below show `git commit` for clarity; in execution route them through the agent with the correct `cwd`.

## File Structure

**Microservice — new dir `ecm_search/` (monorepo root):**

| File | Responsibility |
|---|---|
| `ecm_search/Dockerfile` | Python 3.11 image, pre-bakes embedding model |
| `ecm_search/requirements.txt` | Python deps |
| `ecm_search/.env.example` | Documented env template (versioned) |
| `ecm_search/app/__init__.py` | Package marker |
| `ecm_search/app/config.py` | Reads env vars into a `settings` object |
| `ecm_search/app/odoo_client.py` | Odoo JSON-RPC client (login + call_kw) |
| `ecm_search/app/date_extract.py` | pt-BR month/year regex extractor |
| `ecm_search/app/embedder.py` | sentence-transformers wrapper |
| `ecm_search/app/store.py` | ChromaDB wrapper |
| `ecm_search/app/state.py` | SQLite checkpoint + cycle counter |
| `ecm_search/app/indexer.py` | Builds embedding text, indexes one doc |
| `ecm_search/app/sync.py` | Pull-cron job + reconcile |
| `ecm_search/app/groq_parser.py` | Optional Groq query parse |
| `ecm_search/app/search.py` | Search logic (filters + Chroma query) |
| `ecm_search/app/main.py` | FastAPI app, `/search` `/healthz`, scheduler |
| `ecm_search/tests/test_date_extract.py` | Date extractor tests |
| `ecm_search/tests/test_indexer.py` | Embedding-text composition tests |
| `ecm_search/tests/test_search.py` | where-clause + search tests |
| `ecm_search/tests/test_groq_parser.py` | Groq parse + fallback tests |

**afr_ecm submodule:**

| File | Responsibility |
|---|---|
| `addons/afr_ecm/controllers/semantic_search.py` | Proxy route + ACL filtering |
| `addons/afr_ecm/controllers/__init__.py` | Add import (modify) |
| `addons/afr_ecm/data/semantic_search_data.xml` | `ir.config_parameter` defaults |
| `addons/afr_ecm/__manifest__.py` | Register data file (modify) |
| `addons/afr_ecm/tests/test_semantic_search.py` | Controller proxy + ACL test |

**ecm_desktop submodule:**

| File | Responsibility |
|---|---|
| `ecm_desktop/renderer/lib/ecm-api.ts` | Add `semanticSearch()` wrapper (modify) |
| `ecm_desktop/renderer/components/SemanticSearchPanel.tsx` | Search UI component |
| `ecm_desktop/renderer/app/page.tsx` | Mount the search panel (modify) |

---

> **Design deviation from spec (note for reviewer):** The spec listed `tipo_documento` as a hard ChromaDB filter. Groq returns a fixed enum slug (`nota_fiscal`, …) that will not `$eq`-match the free-text `document_type_id` names configured in afr_ecm. So in this plan, **only `mes`/`ano` are hard filters**; Groq's `tipo_documento`, `keywords_adicionais`, and `entidades` are appended to the query string as soft signals before embedding. The spec file is patched to match.

---

## Task 1: Scaffold microservice (config, deps, FastAPI healthz)

**Files:**
- Create: `ecm_search/requirements.txt`
- Create: `ecm_search/.env.example`
- Create: `ecm_search/app/__init__.py`
- Create: `ecm_search/app/config.py`

- [ ] **Step 1: Create `ecm_search/requirements.txt`**

```txt
fastapi==0.115.6
uvicorn[standard]==0.34.0
chromadb==0.5.23
sentence-transformers==3.3.1
apscheduler==3.11.0
requests==2.32.3
python-dotenv==1.0.1
pytest==8.3.4
```

- [ ] **Step 2: Create `ecm_search/.env.example`**

```env
# Odoo JSON-RPC (conta de serviço, read-only em dms.file)
ODOO_URL=http://web:8069
ODOO_DB=
ODOO_USER=
ODOO_PASSWORD=

# Groq (parse opcional da query no modo "Busca com IA")
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile

# Token compartilhado exigido no header X-Search-Token
SEARCH_TOKEN=

# Sync
SYNC_INTERVAL_MIN=5
RECONCILE_EVERY=12

# Embeddings / store
EMBED_MODEL=paraphrase-multilingual-MiniLM-L12-v2
CHROMA_PATH=/data/chroma
TOP_K=10
```

- [ ] **Step 3: Create `ecm_search/app/__init__.py`** (empty file)

- [ ] **Step 4: Create `ecm_search/app/config.py`**

```python
import os


class Settings:
    odoo_url = os.environ.get("ODOO_URL", "http://web:8069")
    odoo_db = os.environ.get("ODOO_DB", "")
    odoo_user = os.environ.get("ODOO_USER", "")
    odoo_password = os.environ.get("ODOO_PASSWORD", "")
    groq_api_key = os.environ.get("GROQ_API_KEY", "")
    groq_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    search_token = os.environ.get("SEARCH_TOKEN", "")
    sync_interval_min = int(os.environ.get("SYNC_INTERVAL_MIN", "5"))
    reconcile_every = int(os.environ.get("RECONCILE_EVERY", "12"))
    embed_model = os.environ.get("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    chroma_path = os.environ.get("CHROMA_PATH", "/data/chroma")
    top_k = int(os.environ.get("TOP_K", "10"))


settings = Settings()
```

- [ ] **Step 5: Commit**

```bash
# cwd: /home/afonso/docker/odoo_engenapp
git add ecm_search/requirements.txt ecm_search/.env.example ecm_search/app/__init__.py ecm_search/app/config.py
git commit -m "feat(ecm-search): scaffold microservice config e deps"
```

---

## Task 2: pt-BR date extractor (TDD)

**Files:**
- Create: `ecm_search/app/date_extract.py`
- Test: `ecm_search/tests/test_date_extract.py`

- [ ] **Step 1: Write the failing tests**

`ecm_search/tests/test_date_extract.py`:

```python
from app.date_extract import extract_period


def test_numeric_full_date():
    assert extract_period("emitida em 12/03/2025 na sede") == (3, 2025)


def test_month_year_slash():
    assert extract_period("competência 03/2025") == (3, 2025)


def test_month_name():
    assert extract_period("referente a março de 2025") == (3, 2025)


def test_month_abbrev():
    assert extract_period("período mar/2025 fechado") == (3, 2025)


def test_most_frequent_pair_wins():
    text = "01/2024 vence 05/03/2025 e tambem 05/03/2025"
    assert extract_period(text) == (3, 2025)


def test_tie_returns_first():
    assert extract_period("janeiro de 2024 e fevereiro de 2025") == (1, 2024)


def test_no_date_returns_zero():
    assert extract_period("documento sem qualquer data") == (0, 0)


def test_empty_text():
    assert extract_period("") == (0, 0)
    assert extract_period(None) == (0, 0)


def test_invalid_month_ignored():
    assert extract_period("codigo 99/2025 sozinho") == (0, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ecm_search && python -m pytest tests/test_date_extract.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.date_extract'`

- [ ] **Step 3: Write the implementation**

`ecm_search/app/date_extract.py`:

```python
import re
from collections import Counter

_MONTHS = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}

_RE_FULL = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b")
_RE_MY = re.compile(r"\b(\d{1,2})[/\-.](\d{4})\b")
_RE_NAME = re.compile(
    r"\b(" + "|".join(sorted(_MONTHS, key=len, reverse=True)) +
    r")\.?\s*(?:de\s+|/|-)?\s*(\d{4})\b",
    re.IGNORECASE,
)


def _valid(mes, ano):
    return 1 <= mes <= 12 and 1990 <= ano <= 2100


def extract_period(text):
    """Return (mes, ano) most frequent in text; (0, 0) if none found."""
    if not text:
        return (0, 0)
    pairs = []
    for _d, m, a in _RE_FULL.findall(text):
        m, a = int(m), int(a)
        if _valid(m, a):
            pairs.append((m, a))
    text_wo_full = _RE_FULL.sub(" ", text)
    for m, a in _RE_MY.findall(text_wo_full):
        m, a = int(m), int(a)
        if _valid(m, a):
            pairs.append((m, a))
    for name, a in _RE_NAME.findall(text):
        m = _MONTHS[name.lower()]
        a = int(a)
        if _valid(m, a):
            pairs.append((m, a))
    if not pairs:
        return (0, 0)
    counter = Counter(pairs)
    top = counter.most_common(1)[0][1]
    for pair in pairs:
        if counter[pair] == top:
            return pair
    return pairs[0]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ecm_search && python -m pytest tests/test_date_extract.py -v`
Expected: PASS — 9 tests pass.

- [ ] **Step 5: Commit**

```bash
# cwd: /home/afonso/docker/odoo_engenapp
git add ecm_search/app/date_extract.py ecm_search/tests/test_date_extract.py
git commit -m "feat(ecm-search): extrator de mês/ano pt-BR"
```

---

## Task 3: Odoo JSON-RPC client

No unit test — exercised against a live Odoo in Task 11. Keep it small and obviously correct.

**Files:**
- Create: `ecm_search/app/odoo_client.py`

- [ ] **Step 1: Write `ecm_search/app/odoo_client.py`**

```python
import requests


class OdooClient:
    """Minimal Odoo JSON-RPC client (login + execute_kw)."""

    def __init__(self, url, db, user, password):
        self.url = url.rstrip("/")
        self.db = db
        self.user = user
        self.password = password
        self.uid = None

    def _call(self, service, method, args):
        resp = requests.post(
            f"{self.url}/jsonrpc",
            json={
                "jsonrpc": "2.0",
                "method": "call",
                "params": {"service": service, "method": method, "args": args},
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            raise RuntimeError(data["error"])
        return data["result"]

    def login(self):
        self.uid = self._call("common", "login", [self.db, self.user, self.password])
        if not self.uid:
            raise RuntimeError("Odoo login failed")
        return self.uid

    def execute_kw(self, model, method, args, kwargs=None):
        if self.uid is None:
            self.login()
        return self._call(
            "object",
            "execute_kw",
            [self.db, self.uid, self.password, model, method, args, kwargs or {}],
        )

    def search_read(self, model, domain, fields, **kwargs):
        return self.execute_kw(model, "search_read", [domain, fields], kwargs)

    def search(self, model, domain, **kwargs):
        return self.execute_kw(model, "search", [domain], kwargs)
```

- [ ] **Step 2: Commit**

```bash
# cwd: /home/afonso/docker/odoo_engenapp
git add ecm_search/app/odoo_client.py
git commit -m "feat(ecm-search): cliente JSON-RPC do Odoo"
```

---

## Task 4: Embedder + ChromaDB store

No unit tests — thin wrappers over libraries, exercised in Task 11.

**Files:**
- Create: `ecm_search/app/embedder.py`
- Create: `ecm_search/app/store.py`

- [ ] **Step 1: Write `ecm_search/app/embedder.py`**

```python
from sentence_transformers import SentenceTransformer


class Embedder:
    """Wraps a sentence-transformers model; returns plain float lists."""

    def __init__(self, model_name):
        self._model = SentenceTransformer(model_name)

    def encode(self, text):
        return self._model.encode([text])[0].tolist()
```

- [ ] **Step 2: Write `ecm_search/app/store.py`**

```python
import chromadb


class Store:
    """ChromaDB persistent wrapper for the `documentos` collection."""

    def __init__(self, path):
        client = chromadb.PersistentClient(path=path)
        self._col = client.get_or_create_collection(
            name="documentos", metadata={"hnsw:space": "cosine"}
        )

    def upsert(self, doc_id, embedding, document, metadata):
        self._col.upsert(
            ids=[str(doc_id)],
            embeddings=[embedding],
            documents=[document],
            metadatas=[metadata],
        )

    def query(self, embedding, where=None, n_results=10):
        kwargs = {
            "query_embeddings": [embedding],
            "n_results": n_results,
            "include": ["metadatas", "distances", "documents"],
        }
        if where:
            kwargs["where"] = where
        return self._col.query(**kwargs)

    def delete(self, ids):
        if ids:
            self._col.delete(ids=[str(i) for i in ids])

    def all_ids(self):
        return self._col.get(include=[])["ids"]

    def count(self):
        return self._col.count()

    def get_hash(self, doc_id):
        res = self._col.get(ids=[str(doc_id)], include=["metadatas"])
        if res["ids"]:
            return res["metadatas"][0].get("content_hash")
        return None
```

- [ ] **Step 3: Commit**

```bash
# cwd: /home/afonso/docker/odoo_engenapp
git add ecm_search/app/embedder.py ecm_search/app/store.py
git commit -m "feat(ecm-search): wrappers de embedding e ChromaDB"
```

---

## Task 5: Indexer — embedding text composition (TDD)

**Files:**
- Create: `ecm_search/app/indexer.py`
- Test: `ecm_search/tests/test_indexer.py`

- [ ] **Step 1: Write the failing tests**

`ecm_search/tests/test_indexer.py`:

```python
from app.indexer import build_embedding_text, normalize_doc


def test_build_embedding_text_joins_parts():
    doc = {
        "document_type": "Nota Fiscal",
        "directory": "Compras 2025",
        "keywords": ["icms", "fornecedor"],
        "entities": ["XYZ Ltda"],
        "mes": 3,
        "ano": 2025,
    }
    text = build_embedding_text(doc)
    assert "Nota Fiscal" in text
    assert "Compras 2025" in text
    assert "icms" in text
    assert "XYZ Ltda" in text
    assert "mês 3 ano 2025" in text


def test_build_embedding_text_skips_empty_period():
    doc = {"document_type": "Contrato", "directory": "", "keywords": [],
           "entities": [], "mes": 0, "ano": 0}
    text = build_embedding_text(doc)
    assert text == "Contrato"


def test_normalize_doc_parses_odoo_record():
    raw = {
        "id": 42,
        "name": "nf_003.pdf",
        "ocr_text": "nota fiscal de 03/2025",
        "keywords": "icms, fornecedor , compra",
        "entities": '{"ORG": ["XYZ Ltda"], "PER": ["Joao"]}',
        "document_type_id": [7, "Nota Fiscal"],
        "directory_id": [3, "Compras"],
        "ocr_content_hash": "abc123",
    }
    doc = normalize_doc(raw)
    assert doc["dms_file_id"] == 42
    assert doc["document_type"] == "Nota Fiscal"
    assert doc["directory"] == "Compras"
    assert doc["keywords"] == ["icms", "fornecedor", "compra"]
    assert set(doc["entities"]) == {"XYZ Ltda", "Joao"}
    assert doc["mes"] == 3 and doc["ano"] == 2025
    assert doc["content_hash"] == "abc123"


def test_normalize_doc_handles_missing_fields():
    raw = {"id": 9, "name": "x.pdf", "ocr_text": "",
           "keywords": False, "entities": False,
           "document_type_id": False, "directory_id": False,
           "ocr_content_hash": False}
    doc = normalize_doc(raw)
    assert doc["document_type"] == ""
    assert doc["keywords"] == []
    assert doc["entities"] == []
    assert doc["mes"] == 0 and doc["ano"] == 0
    assert doc["content_hash"] == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ecm_search && python -m pytest tests/test_indexer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.indexer'`

- [ ] **Step 3: Write the implementation**

`ecm_search/app/indexer.py`:

```python
import json

from app.date_extract import extract_period


def _name(m2o):
    """Odoo many2one comes back as [id, name] or False."""
    if isinstance(m2o, (list, tuple)) and len(m2o) == 2:
        return m2o[1]
    return ""


def _split_keywords(value):
    if not value:
        return []
    return [k.strip() for k in str(value).split(",") if k.strip()]


def _flatten_entities(value):
    if not value:
        return []
    try:
        data = json.loads(value) if isinstance(value, str) else value
    except (ValueError, TypeError):
        return []
    out = []
    if isinstance(data, dict):
        for vals in data.values():
            if isinstance(vals, list):
                out.extend(str(v) for v in vals)
    return out


def normalize_doc(raw):
    """Turn a dms.file search_read record into the indexer's doc shape."""
    mes, ano = extract_period(raw.get("ocr_text") or "")
    return {
        "dms_file_id": raw["id"],
        "name": raw.get("name") or "",
        "document_type": _name(raw.get("document_type_id")),
        "directory": _name(raw.get("directory_id")),
        "keywords": _split_keywords(raw.get("keywords")),
        "entities": _flatten_entities(raw.get("entities")),
        "mes": mes,
        "ano": ano,
        "content_hash": raw.get("ocr_content_hash") or "",
    }


def build_embedding_text(doc):
    parts = [
        doc.get("document_type", ""),
        doc.get("directory", ""),
        " ".join(doc.get("keywords", [])),
        " ".join(doc.get("entities", [])),
    ]
    if doc.get("ano"):
        parts.append(f"mês {doc.get('mes', 0)} ano {doc['ano']}")
    return " ".join(p for p in parts if p).strip()


def index_doc(raw, embedder, store):
    """Normalize, embed and upsert a dms.file record into the store."""
    doc = normalize_doc(raw)
    text = build_embedding_text(doc)
    embedding = embedder.encode(text)
    metadata = {
        "dms_file_id": doc["dms_file_id"],
        "tipo_documento": doc["document_type"],
        "mes": doc["mes"],
        "ano": doc["ano"],
        "arquivo": doc["name"],
        "directory": doc["directory"],
        "content_hash": doc["content_hash"],
    }
    store.upsert(doc["dms_file_id"], embedding, text, metadata)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ecm_search && python -m pytest tests/test_indexer.py -v`
Expected: PASS — 4 tests pass.

- [ ] **Step 5: Commit**

```bash
# cwd: /home/afonso/docker/odoo_engenapp
git add ecm_search/app/indexer.py ecm_search/tests/test_indexer.py
git commit -m "feat(ecm-search): indexador (normalização + texto de embedding)"
```

---

## Task 6: State (SQLite checkpoint + cycle counter)

No unit test — trivial SQLite wrapper, exercised in Task 11.

**Files:**
- Create: `ecm_search/app/state.py`

- [ ] **Step 1: Write `ecm_search/app/state.py`**

```python
import sqlite3


class State:
    """Persists the sync checkpoint and cycle counter in SQLite."""

    def __init__(self, path):
        self._path = path
        conn = self._conn()
        conn.execute(
            "CREATE TABLE IF NOT EXISTS sync_state ("
            "id INTEGER PRIMARY KEY CHECK (id = 1), "
            "checkpoint TEXT, cycle_count INTEGER)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO sync_state (id, checkpoint, cycle_count) "
            "VALUES (1, '1970-01-01 00:00:00', 0)"
        )
        conn.commit()
        conn.close()

    def _conn(self):
        return sqlite3.connect(self._path)

    def get_checkpoint(self):
        conn = self._conn()
        value = conn.execute(
            "SELECT checkpoint FROM sync_state WHERE id = 1"
        ).fetchone()[0]
        conn.close()
        return value

    def set_checkpoint(self, value):
        conn = self._conn()
        conn.execute("UPDATE sync_state SET checkpoint = ? WHERE id = 1", (value,))
        conn.commit()
        conn.close()

    def get_cycle(self):
        conn = self._conn()
        value = conn.execute(
            "SELECT cycle_count FROM sync_state WHERE id = 1"
        ).fetchone()[0]
        conn.close()
        return value

    def incr_cycle(self):
        conn = self._conn()
        conn.execute("UPDATE sync_state SET cycle_count = cycle_count + 1 WHERE id = 1")
        conn.commit()
        conn.close()
```

- [ ] **Step 2: Commit**

```bash
# cwd: /home/afonso/docker/odoo_engenapp
git add ecm_search/app/state.py
git commit -m "feat(ecm-search): estado de sync em SQLite"
```

---

## Task 7: Sync job (pull cron + reconcile)

No unit test — orchestration glue, validated live in Task 11.

**Files:**
- Create: `ecm_search/app/sync.py`

- [ ] **Step 1: Write `ecm_search/app/sync.py`**

```python
from app.indexer import index_doc

_FIELDS = [
    "id", "name", "ocr_text", "keywords", "entities",
    "document_type_id", "directory_id", "ocr_content_hash", "write_date",
]


def _reconcile(odoo, store):
    """Drop from the index any id no longer present (active) in Odoo."""
    active = odoo.search("dms.file", [])
    active_set = {str(i) for i in active}
    stale = [i for i in store.all_ids() if i not in active_set]
    store.delete(stale)


def sync_once(odoo, embedder, store, state, reconcile_every):
    """One pull cycle: index changed docs, periodically reconcile deletes."""
    checkpoint = state.get_checkpoint()
    docs = odoo.search_read(
        "dms.file",
        [["ocr_state", "=", "done"], ["write_date", ">", checkpoint]],
        _FIELDS,
        order="write_date asc",
        limit=200,
    )
    max_wd = checkpoint
    indexed = 0
    for doc in docs:
        current_hash = doc.get("ocr_content_hash") or ""
        existing_hash = store.get_hash(doc["id"])
        if not (existing_hash and existing_hash == current_hash):
            index_doc(doc, embedder, store)
            indexed += 1
        if doc["write_date"] > max_wd:
            max_wd = doc["write_date"]
    if docs:
        state.set_checkpoint(max_wd)
    state.incr_cycle()
    if state.get_cycle() % reconcile_every == 0:
        _reconcile(odoo, store)
    return indexed
```

- [ ] **Step 2: Commit**

```bash
# cwd: /home/afonso/docker/odoo_engenapp
git add ecm_search/app/sync.py
git commit -m "feat(ecm-search): job de sync (pull + reconcile)"
```

---

## Task 8: Groq query parser (TDD)

**Files:**
- Create: `ecm_search/app/groq_parser.py`
- Test: `ecm_search/tests/test_groq_parser.py`

- [ ] **Step 1: Write the failing tests**

`ecm_search/tests/test_groq_parser.py`:

```python
import json
from unittest.mock import patch, MagicMock

from app.groq_parser import parse_query, EMPTY


def _mock_resp(content):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    return resp


def test_parse_ok():
    payload = json.dumps({
        "tipo_documento": "nota_fiscal", "mes": 3, "ano": 2025,
        "keywords_adicionais": ["compra"], "entidades": ["XYZ"],
    })
    with patch("app.groq_parser.requests.post", return_value=_mock_resp(payload)):
        result = parse_query("nf de compra 03/2025", "key", "model")
    assert result["tipo_documento"] == "nota_fiscal"
    assert result["mes"] == 3 and result["ano"] == 2025
    assert result["keywords_adicionais"] == ["compra"]
    assert result["entidades"] == ["XYZ"]


def test_parse_invalid_json_falls_back():
    with patch("app.groq_parser.requests.post",
               return_value=_mock_resp("desculpe, nao sei")):
        result = parse_query("query qualquer", "key", "model")
    assert result == EMPTY


def test_parse_request_error_falls_back():
    import requests
    with patch("app.groq_parser.requests.post",
               side_effect=requests.RequestException("boom")):
        result = parse_query("query qualquer", "key", "model")
    assert result == EMPTY


def test_parse_keeps_only_known_keys():
    payload = json.dumps({"tipo_documento": "contrato", "lixo": "ignora"})
    with patch("app.groq_parser.requests.post", return_value=_mock_resp(payload)):
        result = parse_query("contrato", "key", "model")
    assert "lixo" not in result
    assert result["tipo_documento"] == "contrato"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ecm_search && python -m pytest tests/test_groq_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.groq_parser'`

- [ ] **Step 3: Write the implementation**

`ecm_search/app/groq_parser.py`:

```python
import json

import requests

EMPTY = {
    "tipo_documento": None,
    "mes": None,
    "ano": None,
    "keywords_adicionais": [],
    "entidades": [],
}

_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

_PROMPT = """Você é um sistema de busca de documentos empresariais brasileiros.
Analise a query do usuário e extraia as informações em JSON.

Query: "{query}"

Retorne APENAS um JSON válido (sem explicações, sem markdown) com os campos:
{{
  "tipo_documento": "nota_fiscal | contrato | laudo | relatorio | outro | null",
  "mes": <number ou null>,
  "ano": <number ou null>,
  "keywords_adicionais": ["termos", "relevantes"],
  "entidades": ["nomes de empresas ou pessoas"]
}}"""


def parse_query(query, api_key, model, endpoint=_ENDPOINT):
    """Parse a natural-language query via Groq. Falls back to EMPTY on failure."""
    try:
        resp = requests.post(
            endpoint,
            timeout=30,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "temperature": 0,
                "max_tokens": 300,
                "messages": [{"role": "user", "content": _PROMPT.format(query=query)}],
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
    except (requests.RequestException, KeyError, ValueError, TypeError):
        return dict(EMPTY)
    return {**EMPTY, **{k: data.get(k, EMPTY[k]) for k in EMPTY}}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ecm_search && python -m pytest tests/test_groq_parser.py -v`
Expected: PASS — 4 tests pass.

- [ ] **Step 5: Commit**

```bash
# cwd: /home/afonso/docker/odoo_engenapp
git add ecm_search/app/groq_parser.py ecm_search/tests/test_groq_parser.py
git commit -m "feat(ecm-search): parser de query via Groq com fallback"
```

---

## Task 9: Search logic (TDD)

**Files:**
- Create: `ecm_search/app/search.py`
- Test: `ecm_search/tests/test_search.py`

- [ ] **Step 1: Write the failing tests**

`ecm_search/tests/test_search.py`:

```python
from unittest.mock import MagicMock

from app.search import build_where, run_search


def test_build_where_no_filters():
    assert build_where(0, 0) is None


def test_build_where_single_filter():
    assert build_where(0, 2025) == {"ano": {"$eq": 2025}}


def test_build_where_two_filters():
    where = build_where(3, 2025)
    assert where == {"$and": [{"mes": {"$eq": 3}}, {"ano": {"$eq": 2025}}]}


def _fake_store(count, query_result=None):
    store = MagicMock()
    store.count.return_value = count
    store.query.return_value = query_result
    return store


def test_run_search_empty_collection_returns_empty():
    embedder = MagicMock()
    store = _fake_store(0)
    out = run_search("qualquer", False, embedder, store, top_k=10)
    assert out["results"] == []
    embedder.encode.assert_not_called()


def test_run_search_returns_ranked_results():
    embedder = MagicMock()
    embedder.encode.return_value = [0.1, 0.2]
    store = _fake_store(
        2,
        {
            "ids": [["10", "11"]],
            "distances": [[0.1, 0.4]],
            "metadatas": [[
                {"dms_file_id": 10, "tipo_documento": "Nota Fiscal",
                 "mes": 3, "ano": 2025, "arquivo": "a.pdf", "directory": "Compras"},
                {"dms_file_id": 11, "tipo_documento": "Contrato",
                 "mes": 0, "ano": 0, "arquivo": "b.pdf", "directory": "Juridico"},
            ]],
            "documents": [["", ""]],
        },
    )
    out = run_search("nf 03/2025", False, embedder, store, top_k=10)
    assert [r["dms_file_id"] for r in out["results"]] == [10, 11]
    assert out["results"][0]["score"] == 0.9
    # date regex pulled the period off the query
    assert out["filters_applied"]["mes"] == 3
    assert out["filters_applied"]["ano"] == 2025


def test_run_search_ai_mode_enriches_query(monkeypatch):
    embedder = MagicMock()
    embedder.encode.return_value = [0.1]
    store = _fake_store(1, {
        "ids": [["5"]], "distances": [[0.2]],
        "metadatas": [[{"dms_file_id": 5, "tipo_documento": "x",
                        "mes": 0, "ano": 0, "arquivo": "x.pdf", "directory": "d"}]],
        "documents": [[""]],
    })

    def fake_parse(query, api_key, model):
        return {"tipo_documento": "nota_fiscal", "mes": 7, "ano": 2024,
                "keywords_adicionais": ["compra"], "entidades": ["XYZ"]}

    monkeypatch.setattr("app.search.parse_query", fake_parse)
    out = run_search("achar docs", True, embedder, store, top_k=10,
                     groq_api_key="k", groq_model="m")
    # Groq period overrides; tipo/keywords/entidades appended to embedded text
    assert out["filters_applied"]["mes"] == 7
    assert out["filters_applied"]["ano"] == 2024
    embedded = embedder.encode.call_args[0][0]
    assert "nota_fiscal" in embedded and "compra" in embedded and "XYZ" in embedded
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ecm_search && python -m pytest tests/test_search.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.search'`

- [ ] **Step 3: Write the implementation**

`ecm_search/app/search.py`:

```python
from app.date_extract import extract_period
from app.groq_parser import parse_query


def build_where(mes, ano):
    """ChromaDB where-clause. Only mes/ano are hard filters."""
    conds = []
    if mes:
        conds.append({"mes": {"$eq": mes}})
    if ano:
        conds.append({"ano": {"$eq": ano}})
    if len(conds) > 1:
        return {"$and": conds}
    if conds:
        return conds[0]
    return None


def run_search(query, ai_mode, embedder, store, top_k,
               groq_api_key=None, groq_model=None):
    """Parse, filter and rank. Returns {results, filters_applied}."""
    mes, ano = extract_period(query)
    enriched = query
    if ai_mode and groq_api_key:
        parsed = parse_query(query, groq_api_key, groq_model)
        if parsed.get("mes"):
            mes = parsed["mes"]
        if parsed.get("ano"):
            ano = parsed["ano"]
        extra = []
        if parsed.get("tipo_documento"):
            extra.append(str(parsed["tipo_documento"]))
        extra.extend(str(k) for k in (parsed.get("keywords_adicionais") or []))
        extra.extend(str(e) for e in (parsed.get("entidades") or []))
        if extra:
            enriched = query + " " + " ".join(extra)

    count = store.count()
    if count == 0:
        return {"results": [], "filters_applied": {}}

    where = build_where(mes, ano)
    embedding = embedder.encode(enriched)
    n_results = max(1, min(top_k, count))
    res = store.query(embedding, where=where, n_results=n_results)

    results = []
    ids = res["ids"][0] if res.get("ids") else []
    for i in range(len(ids)):
        md = res["metadatas"][0][i]
        results.append({
            "dms_file_id": md["dms_file_id"],
            "score": round(1 - res["distances"][0][i], 4),
            "tipo": md.get("tipo_documento", ""),
            "mes": md.get("mes", 0),
            "ano": md.get("ano", 0),
            "arquivo": md.get("arquivo", ""),
            "directory": md.get("directory", ""),
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    return {"results": results,
            "filters_applied": {"mes": mes, "ano": ano}}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ecm_search && python -m pytest tests/test_search.py -v`
Expected: PASS — 6 tests pass.

- [ ] **Step 5: Run the full microservice test suite**

Run: `cd ecm_search && python -m pytest -v`
Expected: PASS — all tests from Tasks 2, 5, 8, 9 pass (23 total).

- [ ] **Step 6: Commit**

```bash
# cwd: /home/afonso/docker/odoo_engenapp
git add ecm_search/app/search.py ecm_search/tests/test_search.py
git commit -m "feat(ecm-search): lógica de busca (filtros + ranking)"
```

---

## Task 10: FastAPI app + scheduler

No unit test — wiring; validated live in Task 11.

**Files:**
- Create: `ecm_search/app/main.py`

- [ ] **Step 1: Write `ecm_search/app/main.py`**

```python
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
    if not settings.search_token or x_search_token != settings.search_token:
        raise HTTPException(status_code=401, detail="invalid token")
    return run_search(
        req.query, req.ai_mode, _ctx["embedder"], _ctx["store"],
        req.top_k or settings.top_k,
        settings.groq_api_key, settings.groq_model,
    )


@app.get("/healthz")
def healthz():
    return {"status": "ok", "indexed": _ctx["store"].count()}
```

- [ ] **Step 2: Commit**

```bash
# cwd: /home/afonso/docker/odoo_engenapp
git add ecm_search/app/main.py
git commit -m "feat(ecm-search): app FastAPI + scheduler de sync"
```

---

## Task 11: Dockerfile + docker-compose service (live validation)

**Files:**
- Create: `ecm_search/Dockerfile`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Write `ecm_search/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pré-baixa o modelo de embedding na imagem (camada cacheada)
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

COPY app ./app

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 2: Add the `ecm-search` service to `docker-compose.yml`**

Insert after the `ocr_worker` service block (before `db:`):

```yaml
  ecm-search:
    # Microserviço de busca semântica. Sem porta pública — só rede interna.
    build: ./ecm_search
    tty: true
    env_file:
      - ./ecm_search/.env
    depends_on:
      - web
      - db
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "3"
    volumes:
      - ./data/chroma:/data/chroma
```

- [ ] **Step 3: Create the real `.env` (not versioned)**

Copy `ecm_search/.env.example` to `ecm_search/.env` and fill: `ODOO_DB`,
`ODOO_USER`, `ODOO_PASSWORD` (a read-only Odoo service account), `GROQ_API_KEY`,
and a random `SEARCH_TOKEN`.

Run: `cp ecm_search/.env.example ecm_search/.env` then edit.

- [ ] **Step 4: Add `.env` to `.gitignore`**

Append to `/home/afonso/docker/odoo_engenapp/.gitignore`:

```
ecm_search/.env
data/chroma/
```

- [ ] **Step 5: Build and start the service**

Run: `cd /home/afonso/docker/odoo_engenapp && docker compose build ecm-search && docker compose up -d ecm-search`
Expected: container starts, no crash in `docker compose logs ecm-search`.

- [ ] **Step 6: Verify health and wait for first sync**

Run: `docker compose exec ecm-search python -c "import requests; print(requests.get('http://localhost:8080/healthz').json())"`
Expected: `{'status': 'ok', 'indexed': 0}` initially; after `SYNC_INTERVAL_MIN` minutes, `indexed` > 0 (logs show `[sync] indexed N docs`).

- [ ] **Step 7: Smoke-test `/search` from inside the container**

Run:
```bash
docker compose exec ecm-search python -c "import requests, os; \
print(requests.post('http://localhost:8080/search', \
json={'query':'nota fiscal'}, \
headers={'X-Search-Token': os.environ['SEARCH_TOKEN']}).json())"
```
Expected: JSON with a `results` list (may be empty until docs are indexed).

- [ ] **Step 8: Commit**

```bash
# cwd: /home/afonso/docker/odoo_engenapp
git add ecm_search/Dockerfile docker-compose.yml .gitignore
git commit -m "feat(ecm-search): Dockerfile e serviço no docker-compose"
```

---

## Task 12: afr_ecm proxy controller

**Files:**
- Create: `addons/afr_ecm/controllers/semantic_search.py`
- Modify: `addons/afr_ecm/controllers/__init__.py`
- Create: `addons/afr_ecm/data/semantic_search_data.xml`
- Modify: `addons/afr_ecm/__manifest__.py`
- Test: `addons/afr_ecm/tests/test_semantic_search.py`

- [ ] **Step 1: Write the controller `addons/afr_ecm/controllers/semantic_search.py`**

```python
import logging

import requests

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SemanticSearchController(http.Controller):
    """Proxy autenticado para o microserviço ecm-search, aplicando ACL."""

    @http.route("/afr_ecm/semantic_search", type="json", auth="user")
    def semantic_search(self, query, ai_mode=False, **kw):
        params = request.env["ir.config_parameter"].sudo()
        url = params.get_param("afr_ecm.search.url")
        token = params.get_param("afr_ecm.search.token")
        if not url:
            return {"error": "search service not configured", "results": []}

        try:
            resp = requests.post(
                url.rstrip("/") + "/search",
                json={"query": query or "", "ai_mode": bool(ai_mode)},
                headers={"X-Search-Token": token or ""},
                timeout=30,
            )
            resp.raise_for_status()
            payload = resp.json()
        except requests.RequestException as exc:
            _logger.warning("semantic search backend error: %s", exc)
            return {"error": "search backend unavailable", "results": []}

        raw = payload.get("results", [])
        by_id = {r["dms_file_id"]: r for r in raw}
        # search() aplica record rules + ACL: só retorna ids legíveis pelo usuário.
        files = request.env["dms.file"].search([("id", "in", list(by_id))])
        out = []
        for rec in files:
            hit = by_id.get(rec.id)
            if not hit:
                continue
            out.append({
                "id": rec.id,
                "name": rec.name,
                "directory": rec.directory_id.display_name or "",
                "mimetype": rec.mimetype or "",
                "score": hit.get("score", 0.0),
                "tipo": hit.get("tipo", ""),
                "mes": hit.get("mes", 0),
                "ano": hit.get("ano", 0),
            })
        out.sort(key=lambda r: r["score"], reverse=True)
        return {"results": out,
                "filters_applied": payload.get("filters_applied", {})}
```

- [ ] **Step 2: Register the controller in `addons/afr_ecm/controllers/__init__.py`**

Add this line alongside the existing imports:

```python
from . import semantic_search
```

- [ ] **Step 3: Create `addons/afr_ecm/data/semantic_search_data.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <record id="search_url_param" model="ir.config_parameter">
            <field name="key">afr_ecm.search.url</field>
            <field name="value">http://ecm-search:8080</field>
        </record>
        <record id="search_token_param" model="ir.config_parameter">
            <field name="key">afr_ecm.search.token</field>
            <field name="value"></field>
        </record>
    </data>
</odoo>
```

- [ ] **Step 4: Register the data file in `addons/afr_ecm/__manifest__.py`**

Add `"data/semantic_search_data.xml"` to the `"data"` list.

- [ ] **Step 5: Write the failing test `addons/afr_ecm/tests/test_semantic_search.py`**

```python
from unittest.mock import patch, MagicMock

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestSemanticSearchController(HttpCase):

    def _backend_payload(self, ids):
        return {
            "results": [
                {"dms_file_id": i, "score": 0.9 - n * 0.1,
                 "tipo": "Nota Fiscal", "mes": 3, "ano": 2025}
                for n, i in enumerate(ids)
            ],
            "filters_applied": {"mes": 3, "ano": 2025},
        }

    def test_proxy_filters_by_acl(self):
        """Documentos sem permissão do usuário não aparecem no resultado."""
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("afr_ecm.search.url", "http://ecm-search:8080")
        params.set_param("afr_ecm.search.token", "tok")

        storage = self.env["dms.storage"].create({"name": "S", "save_type": "database"})
        directory = self.env["dms.directory"].create(
            {"name": "D", "root_storage_id": storage.id})
        readable = self.env["dms.file"].create(
            {"name": "ok.pdf", "directory_id": directory.id,
             "content": "dGVzdA=="})

        backend = self._backend_payload([readable.id, 999999])
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = backend

        self.authenticate("admin", "admin")
        with patch("odoo.addons.afr_ecm.controllers.semantic_search.requests.post",
                   return_value=mock_resp):
            result = self.url_open(
                "/afr_ecm/semantic_search",
                data='{"jsonrpc":"2.0","method":"call","params":'
                     '{"query":"nf 03/2025","ai_mode":false}}',
                headers={"Content-Type": "application/json"},
            ).json()

        ids = [r["id"] for r in result["result"]["results"]]
        self.assertIn(readable.id, ids)
        self.assertNotIn(999999, ids)  # id inexistente removido pela ACL
```

- [ ] **Step 6: Run the test to verify it fails**

Run: `docker compose exec web odoo --test-enable --stop-after-init -d <db> -u afr_ecm --test-tags /afr_ecm:TestSemanticSearchController`
Expected: FAIL — controller route not found (module not yet upgraded with the new file).

- [ ] **Step 7: Upgrade the module and re-run the test**

Run the same command. The upgrade loads the new controller + data file.
Expected: PASS — the ACL test passes.

- [ ] **Step 8: Commit (afr_ecm submodule)**

```bash
# cwd: /home/afonso/docker/odoo_engenapp/addons/afr_ecm
git add controllers/semantic_search.py controllers/__init__.py \
        data/semantic_search_data.xml __manifest__.py \
        tests/test_semantic_search.py
git commit -m "feat(afr_ecm): controller proxy de busca semântica com ACL"
git push origin main
```

---

## Task 13: ecm_desktop API wrapper

**Files:**
- Modify: `ecm_desktop/renderer/lib/ecm-api.ts`

- [ ] **Step 1: Inspect `ecm-api.ts`**

Read `ecm_desktop/renderer/lib/ecm-api.ts` to find the existing helper that
calls Odoo JSON-RPC routes through the `/api/odoo/...` proxy (used by other
`/afr_ecm/...` or dataset calls). Reuse that helper's pattern.

- [ ] **Step 2: Add the `semanticSearch` wrapper**

Append to `ecm-api.ts` (adapt the call helper name to whatever the file uses):

```typescript
export interface SemanticSearchHit {
  id: number;
  name: string;
  directory: string;
  mimetype: string;
  score: number;
  tipo: string;
  mes: number;
  ano: number;
}

export interface SemanticSearchResponse {
  results: SemanticSearchHit[];
  filters_applied?: { mes?: number; ano?: number };
  error?: string;
}

export async function semanticSearch(
  query: string,
  aiMode: boolean,
): Promise<SemanticSearchResponse> {
  // callOdoo = helper já existente que faz POST JSON-RPC via /api/odoo proxy
  const result = await callOdoo("/afr_ecm/semantic_search", {
    query,
    ai_mode: aiMode,
  });
  return result as SemanticSearchResponse;
}
```

- [ ] **Step 3: Type-check**

Run: `cd ecm_desktop/renderer && npx tsc --noEmit`
Expected: no new type errors.

- [ ] **Step 4: Commit (ecm_desktop submodule)**

```bash
# cwd: /home/afonso/docker/odoo_engenapp/ecm_desktop
git add renderer/lib/ecm-api.ts
git commit -m "feat(ecm_desktop): wrapper semanticSearch na ecm-api"
git push origin main
```

---

## Task 14: ecm_desktop search UI

No automated test — the renderer has no test harness; validated manually in Task 15.

**Files:**
- Create: `ecm_desktop/renderer/components/SemanticSearchPanel.tsx`
- Modify: `ecm_desktop/renderer/app/page.tsx`

- [ ] **Step 1: Create `SemanticSearchPanel.tsx`**

```tsx
"use client";

import { useState } from "react";
import { semanticSearch, SemanticSearchHit } from "@/lib/ecm-api";

interface Props {
  onOpenFile: (fileId: number) => void;
}

export function SemanticSearchPanel({ onOpenFile }: Props) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SemanticSearchHit[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  async function doSearch(aiMode: boolean) {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await semanticSearch(query, aiMode);
      if (res.error) setError(res.error);
      setHits(res.results || []);
      setSearched(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "erro na busca");
      setHits([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-3 p-4">
      <div className="flex gap-2">
        <input
          className="flex-1 rounded border px-3 py-2 text-sm"
          placeholder="Buscar documentos em linguagem natural..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && doSearch(false)}
        />
        <button
          className="rounded bg-primary px-3 py-2 text-sm text-primary-foreground"
          onClick={() => doSearch(false)}
          disabled={loading}
        >
          Buscar
        </button>
        <button
          className="rounded border px-3 py-2 text-sm"
          onClick={() => doSearch(true)}
          disabled={loading}
          title="Usa IA (Groq) para interpretar a busca"
        >
          Busca com IA
        </button>
      </div>

      {loading && <p className="text-sm text-muted-foreground">Buscando...</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}
      {!loading && searched && hits.length === 0 && !error && (
        <p className="text-sm text-muted-foreground">Nenhum resultado.</p>
      )}

      <ul className="flex flex-col gap-1">
        {hits.map((hit) => (
          <li
            key={hit.id}
            className="flex cursor-pointer items-center justify-between rounded border px-3 py-2 text-sm hover:bg-accent"
            onClick={() => onOpenFile(hit.id)}
          >
            <span className="flex flex-col">
              <span className="font-medium">{hit.name}</span>
              <span className="text-xs text-muted-foreground">
                {hit.directory}
                {hit.tipo ? ` · ${hit.tipo}` : ""}
                {hit.ano ? ` · ${hit.mes}/${hit.ano}` : ""}
              </span>
            </span>
            <span className="text-xs font-mono text-muted-foreground">
              {(hit.score * 100).toFixed(0)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: Mount the panel in `app/page.tsx`**

Read `ecm_desktop/renderer/app/page.tsx`. Add `SemanticSearchPanel` to the
layout (e.g. in a collapsible sidebar section or a dialog). Wire `onOpenFile`
to the existing file-preview opener used by the file list (the handler that
opens `FilePreviewModal` for a given `dms.file` id).

```tsx
import { SemanticSearchPanel } from "@/components/SemanticSearchPanel";

// dentro do componente, onde já existe o handler de abrir preview:
<SemanticSearchPanel onOpenFile={(id) => openPreviewForFileId(id)} />
```

- [ ] **Step 3: Type-check**

Run: `cd ecm_desktop/renderer && npx tsc --noEmit`
Expected: no new type errors.

- [ ] **Step 4: Run the dev server and visually verify**

Run: `cd ecm_desktop/renderer && npm run dev` → open `http://localhost:3000`.
Verify: search box renders, typing + "Buscar" returns results, clicking a
result opens the preview, "Busca com IA" button works, empty state shows
"Nenhum resultado.".

- [ ] **Step 5: Commit (ecm_desktop submodule)**

```bash
# cwd: /home/afonso/docker/odoo_engenapp/ecm_desktop
git add renderer/components/SemanticSearchPanel.tsx renderer/app/page.tsx
git commit -m "feat(ecm_desktop): painel de busca semântica"
git push origin main
```

---

## Task 15: End-to-end integration + submodule bump

- [ ] **Step 1: Full stack up**

Run: `cd /home/afonso/docker/odoo_engenapp && docker compose up -d`
Verify all containers healthy: `docker compose ps`.

- [ ] **Step 2: Confirm indexing**

Wait one sync cycle. Run the `/healthz` check from Task 11 Step 6.
Expected: `indexed` matches the count of `dms.file` records with `ocr_state=done`.

- [ ] **Step 3: Natural-language query matrix**

In the ecm_desktop UI, run queries and confirm sensible ranking:
- "notas fiscais de compra do mês 03 de 2025"
- "contratos com a empresa XYZ"
- "laudos técnicos de janeiro"
- Same queries with **"Busca com IA"** — confirm Groq parse changes results.
- A query that matches nothing — confirm "Nenhum resultado.".

- [ ] **Step 4: Confirm ACL**

Log into ecm_desktop as a non-admin user with restricted directory access.
Confirm search results exclude documents in directories they cannot read.

- [ ] **Step 5: Confirm reconcile**

Move an indexed document to the trash in Odoo. After `RECONCILE_EVERY` sync
cycles, confirm it no longer appears in search results.

- [ ] **Step 6: Bump submodule pointers in the monorepo**

```bash
# cwd: /home/afonso/docker/odoo_engenapp
git add addons/afr_ecm ecm_desktop
git commit -m "chore: bump afr_ecm e ecm_desktop (busca semântica)"
git push
```

- [ ] **Step 7: Push the monorepo `ecm_search/` work**

```bash
# cwd: /home/afonso/docker/odoo_engenapp
git push
```

---

## Self-Review

**Spec coverage:**
- Microserviço dedicado → Tasks 1–11. ✓
- Pull cron + reconcile → Task 7. ✓
- Extração regex de mês/ano → Task 2. ✓
- Busca padrão + "Busca com IA" Groq → Tasks 8, 9, 14. ✓
- Controller proxy afr_ecm + ACL → Task 12. ✓
- Config params → Task 12 Step 3. ✓
- UI ecm_desktop → Tasks 13, 14. ✓
- Coleção vazia + fallback JSON Groq → Task 9 (`run_search` empty guard), Task 8 (`EMPTY` fallback). ✓
- Testes → Tasks 2, 5, 8, 9 (microserviço), 12 (controller); integração manual Task 15. ✓
- Docker → Task 11. ✓
- Segurança (token, sem porta pública, ACL, .env não versionado) → Tasks 11, 12. ✓

**Deviation from spec:** `tipo_documento` is a soft signal (appended to embedded query text), not a hard ChromaDB filter — Groq's enum slug cannot `$eq`-match free-text `document_type_id` names. Spec file patched accordingly.

**Type consistency:** `extract_period` returns `(mes, ano)` tuple — used consistently in Tasks 2, 5, 9. `run_search` / `build_where` signatures match `main.py` call site. `normalize_doc` output keys match `build_embedding_text` and `index_doc` reads. `SemanticSearchHit` fields match the controller's returned dict. ✓

**Placeholder scan:** No TBD/TODO. The only `<db>` placeholder (Task 12 Steps 6–7) is an intentional runtime value (the Odoo database name), not a plan gap.
