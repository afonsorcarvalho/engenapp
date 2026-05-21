import hashlib
from unittest.mock import MagicMock

from app.indexer import build_embedding_text, index_doc, normalize_doc

_RAW = {
    "id": 42,
    "name": "nf_003.pdf",
    "ocr_text": "nota fiscal de 03/2025",
    "keywords": "icms, fornecedor",
    "entities": '{"ORG": ["XYZ Ltda"]}',
    "document_type_id": [7, "Nota Fiscal"],
    "directory_id": [3, "Compras"],
    "ocr_content_hash": "abc123",
    "write_date": "2025-03-01 10:00:00",
}


def _text_hash_of(raw):
    return hashlib.sha256(
        build_embedding_text(normalize_doc(raw)).encode("utf-8")
    ).hexdigest()


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


def test_index_doc_skips_when_text_hash_matches():
    embedder = MagicMock()
    store = MagicMock()
    store.get_hash.return_value = _text_hash_of(_RAW)
    result = index_doc(_RAW, embedder, store)
    assert result is False
    embedder.encode.assert_not_called()
    store.upsert.assert_not_called()


def test_index_doc_indexes_when_text_hash_differs():
    embedder = MagicMock()
    embedder.encode.return_value = [0.1, 0.2]
    store = MagicMock()
    store.get_hash.return_value = "stale-hash"
    result = index_doc(_RAW, embedder, store)
    assert result is True
    embedder.encode.assert_called_once()
    store.upsert.assert_called_once()
    # content_hash stored in metadata is the embedding-text sha256
    metadata = store.upsert.call_args[0][3]
    assert metadata["content_hash"] == _text_hash_of(_RAW)


def test_index_doc_indexes_when_store_empty():
    embedder = MagicMock()
    embedder.encode.return_value = [0.1]
    store = MagicMock()
    store.get_hash.return_value = None
    assert index_doc(_RAW, embedder, store) is True
    embedder.encode.assert_called_once()
