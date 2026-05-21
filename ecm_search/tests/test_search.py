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
