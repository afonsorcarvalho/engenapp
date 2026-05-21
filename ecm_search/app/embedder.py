from sentence_transformers import SentenceTransformer


class Embedder:
    """Wraps a sentence-transformers model; returns plain float lists."""

    def __init__(self, model_name):
        self._model = SentenceTransformer(model_name)

    def encode(self, text):
        return self._model.encode([text])[0].tolist()
