import chromadb


class Store:
    """ChromaDB persistent wrapper for the `documentos` collection."""

    _NAME = "documentos"

    def __init__(self, path):
        self._client = chromadb.PersistentClient(path=path)
        self._col = self._client.get_or_create_collection(
            name=self._NAME, metadata={"hnsw:space": "cosine"}
        )

    def reset(self):
        """Drop and recreate the collection — used when the embedding model
        changes, since vectors from different models are not comparable."""
        try:
            self._client.delete_collection(self._NAME)
        except Exception:
            pass  # collection may not exist yet
        self._col = self._client.get_or_create_collection(
            name=self._NAME, metadata={"hnsw:space": "cosine"}
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
