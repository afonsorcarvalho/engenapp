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


def _fake_reranker(scores):
    r = MagicMock()
    r.rerank.return_value = scores
    return r


def _result(ids, metadatas, documents):
    return {"ids": [ids], "metadatas": [metadatas], "documents": [documents]}


def _md(doc_id, **kw):
    base = {"dms_file_id": doc_id, "tipo_documento": "x", "mes": 0, "ano": 0,
            "arquivo": f"{doc_id}.pdf", "directory": "d"}
    base.update(kw)
    return base


def test_run_search_empty_collection_returns_empty():
    embedder = MagicMock()
    reranker = _fake_reranker([])
    out = run_search("qualquer", False, embedder, _fake_store(0), reranker, top_k=10)
    assert out["results"] == []
    embedder.encode_query.assert_not_called()
    reranker.rerank.assert_not_called()


def test_run_search_reranker_scores_drive_ranking():
    embedder = MagicMock()
    embedder.encode_query.return_value = [0.1, 0.2]
    store = _fake_store(2, _result(
        ["10", "11"],
        [_md(10, tipo_documento="Nota Fiscal", mes=3, ano=2025),
         _md(11, tipo_documento="Contrato")],
        ["doc dez", "doc onze"],
    ))
    # bi-encoder devolve [10, 11]; reranker pontua 11 acima de 10
    reranker = _fake_reranker([0.20, 0.95])
    out = run_search("nf 03/2025", False, embedder, store, reranker, top_k=10)
    assert [r["dms_file_id"] for r in out["results"]] == [11, 10]
    assert out["results"][0]["score"] == 0.95
    assert out["filters_applied"]["mes"] == 3
    assert out["filters_applied"]["ano"] == 2025


def test_run_search_reranker_gets_original_query_not_enriched(monkeypatch):
    embedder = MagicMock()
    embedder.encode_query.return_value = [0.1]
    store = _fake_store(1, _result(["5"], [_md(5)], ["doc cinco"]))
    reranker = _fake_reranker([0.8])

    def fake_parse(query, api_key, model):
        return {"tipo_documento": "nota_fiscal", "mes": 7, "ano": 2024,
                "keywords_adicionais": ["compra"], "entidades": ["XYZ"]}

    monkeypatch.setattr("app.search.parse_query", fake_parse)
    out = run_search("achar docs", True, embedder, store, reranker, top_k=10,
                     groq_api_key="k", groq_model="m")
    assert out["filters_applied"]["mes"] == 7
    assert out["filters_applied"]["ano"] == 2024
    # e5 recebe a query enriquecida com termos do Groq
    embedded = embedder.encode_query.call_args[0][0]
    assert "nota_fiscal" in embedded and "compra" in embedded and "XYZ" in embedded
    # reranker recebe a query ORIGINAL, sem enriquecimento
    assert reranker.rerank.call_args[0][0] == "achar docs"


def test_run_search_min_score_drops_low_results():
    embedder = MagicMock()
    embedder.encode_query.return_value = [0.1]
    store = _fake_store(2, _result(
        ["10", "11"], [_md(10), _md(11)], ["d10", "d11"]))
    reranker = _fake_reranker([0.9, 0.3])
    out = run_search("q", False, embedder, store, reranker, top_k=10, min_score=0.5)
    assert [r["dms_file_id"] for r in out["results"]] == [10]
    assert out["filters_applied"]["min_score"] == 0.5


def test_run_search_min_score_zero_keeps_all():
    embedder = MagicMock()
    embedder.encode_query.return_value = [0.1]
    store = _fake_store(2, _result(
        ["10", "11"], [_md(10), _md(11)], ["d10", "d11"]))
    reranker = _fake_reranker([0.9, 0.3])
    out = run_search("q", False, embedder, store, reranker, top_k=10, min_score=0.0)
    assert len(out["results"]) == 2


def test_run_search_rel_cutoff_drops_trailing_results():
    embedder = MagicMock()
    embedder.encode_query.return_value = [0.1]
    store = _fake_store(3, _result(
        ["10", "11", "12"], [_md(10), _md(11), _md(12)], ["d10", "d11", "d12"]))
    reranker = _fake_reranker([0.9, 0.65, 0.4])
    # best=0.9, rel_cutoff 0.8 -> floor 0.72; keeps only 0.9
    out = run_search("q", False, embedder, store, reranker, top_k=10, rel_cutoff=0.8)
    assert [r["dms_file_id"] for r in out["results"]] == [10]
    assert out["filters_applied"]["rel_cutoff"] == 0.8


def test_run_search_caps_at_top_k():
    embedder = MagicMock()
    embedder.encode_query.return_value = [0.1]
    ids = [str(i) for i in range(5)]
    store = _fake_store(5, _result(
        ids, [_md(i) for i in range(5)], [f"d{i}" for i in range(5)]))
    reranker = _fake_reranker([0.9, 0.8, 0.7, 0.6, 0.5])
    out = run_search("q", False, embedder, store, reranker, top_k=3)
    assert len(out["results"]) == 3
    assert [r["dms_file_id"] for r in out["results"]] == [0, 1, 2]
