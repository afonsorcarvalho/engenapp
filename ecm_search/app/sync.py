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


_PAGE_SIZE = 200


def sync_once(odoo, embedder, store, state, reconcile_every):
    """One pull cycle: index changed docs, periodically reconcile deletes.

    Pages through every doc with write_date >= checkpoint. The `>=` plus a
    text-hash skip in index_doc makes boundary docs idempotent: they are
    re-fetched each cycle but skipped at the encode step when unchanged.
    """
    checkpoint = state.get_checkpoint()
    domain = [["ocr_state", "=", "done"], ["write_date", ">=", checkpoint]]
    max_wd = checkpoint
    indexed = 0
    pulled = 0
    offset = 0
    while True:
        docs = odoo.search_read(
            "dms.file", domain, _FIELDS,
            order="write_date asc, id asc",
            limit=_PAGE_SIZE, offset=offset,
        )
        for doc in docs:
            if index_doc(doc, embedder, store):
                indexed += 1
            if doc["write_date"] > max_wd:
                max_wd = doc["write_date"]
        pulled += len(docs)
        if len(docs) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE
    if pulled:
        state.set_checkpoint(max_wd)
    state.incr_cycle()
    if state.get_cycle() % reconcile_every == 0:
        _reconcile(odoo, store)
    return indexed
