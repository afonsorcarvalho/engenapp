from sentence_transformers import SentenceTransformer


class Embedder:
    """Wraps a sentence-transformers model; returns plain float lists.

    Modelos da família e5 exigem prefixos assimétricos: a query recebe
    "query: " e o documento recebe "passage: ". Sem isso o retrieval degrada.
    Para modelos não-e5 os prefixos não são aplicados.
    """

    def __init__(self, model_name):
        self._model = SentenceTransformer(model_name)
        self._e5 = "e5" in model_name.lower()

    def _encode(self, text):
        return self._model.encode([text])[0].tolist()

    def encode_query(self, text):
        return self._encode(f"query: {text}" if self._e5 else text)

    def encode_passage(self, text):
        return self._encode(f"passage: {text}" if self._e5 else text)
