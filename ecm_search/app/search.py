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
