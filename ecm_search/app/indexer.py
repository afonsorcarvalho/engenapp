import hashlib
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
    """Normalize, embed and upsert a dms.file record into the store.

    Skips re-embedding when the store already holds a vector built from the
    same embedding text. Returns True if the doc was (re)indexed, False if
    skipped because nothing relevant changed.
    """
    doc = normalize_doc(raw)
    text = build_embedding_text(doc)
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if store.get_hash(doc["dms_file_id"]) == text_hash:
        return False
    embedding = embedder.encode(text)
    metadata = {
        "dms_file_id": doc["dms_file_id"],
        "tipo_documento": doc["document_type"],
        "mes": doc["mes"],
        "ano": doc["ano"],
        "arquivo": doc["name"],
        "directory": doc["directory"],
        "content_hash": text_hash,
    }
    store.upsert(doc["dms_file_id"], embedding, text, metadata)
    return True
