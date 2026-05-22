import json

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


# Quantos candidatos o bi-encoder recupera para o reranker re-pontuar.
_CANDIDATE_MULT = 4
_CANDIDATE_MIN = 30


def run_search(query, ai_mode, embedder, store, reranker, top_k,
               groq_api_key=None, groq_model=None, min_score=0.0,
               rel_cutoff=0.0):
    """Parse, retrieve, rerank, filter. Returns {results, filters_applied}.

    Pipeline: e5 (bi-encoder) recupera um conjunto amplo de candidatos →
    cross-encoder re-pontua cada (query, documento) → filtros sobre o score
    do reranker, que separa relevante de ruído de verdade.

    Filtros de ruído:
    - `min_score`: piso absoluto — descarta abaixo deste score do reranker.
    - `rel_cutoff`: piso relativo — descarta abaixo de `rel_cutoff` vezes o
      score do melhor resultado.
    """
    mes, ano = extract_period(query)
    enriched = query
    ai_parse = None
    if ai_mode and groq_api_key:
        parsed = parse_query(query, groq_api_key, groq_model)
        ai_parse = parsed
        print(f"[search] query={query!r} groq_parse={json.dumps(parsed, ensure_ascii=False)}")
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
        return {"results": [], "filters_applied": {}, "ai_parse": ai_parse}

    where = build_where(mes, ano)
    embedding = embedder.encode_query(enriched)
    cand_n = max(1, min(max(top_k * _CANDIDATE_MULT, _CANDIDATE_MIN), count))
    res = store.query(embedding, where=where, n_results=cand_n)

    ids = res["ids"][0] if res.get("ids") else []
    cands = []
    for i in range(len(ids)):
        md = res["metadatas"][0][i]
        cands.append({
            "dms_file_id": md["dms_file_id"],
            "tipo": md.get("tipo_documento", ""),
            "mes": md.get("mes", 0),
            "ano": md.get("ano", 0),
            "arquivo": md.get("arquivo", ""),
            "directory": md.get("directory", ""),
            "_document": res["documents"][0][i],
        })

    # Rerank com a query original (sem o enriquecimento Groq) — o cross-encoder
    # lida melhor com a query natural; o enriquecimento serve só ao recall do e5.
    scores = reranker.rerank(query, [c["_document"] for c in cands])
    results = []
    for cand, score in zip(cands, scores):
        cand.pop("_document", None)
        cand["score"] = round(float(score), 4)
        results.append(cand)

    if min_score > 0:
        results = [r for r in results if r["score"] >= min_score]
    results.sort(key=lambda r: r["score"], reverse=True)
    if rel_cutoff > 0 and results:
        floor = results[0]["score"] * rel_cutoff
        results = [r for r in results if r["score"] >= floor]
    results = results[:top_k]
    return {"results": results,
            "filters_applied": {"mes": mes, "ano": ano,
                                "min_score": min_score, "rel_cutoff": rel_cutoff},
            "ai_parse": ai_parse}
