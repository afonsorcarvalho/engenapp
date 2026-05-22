import math

import torch
from sentence_transformers import CrossEncoder


class Reranker:
    """Cross-encoder: re-pontua pares (query, documento) com atenção real
    query×documento — separa relevante de ruído muito melhor que o cosseno
    do bi-encoder. Roda só sobre os candidatos já recuperados pelo e5.

    Força ativação Identity e aplica sigmoid aqui, para o score sair sempre
    normalizado em 0-1 independente do modelo.
    """

    def __init__(self, model_name):
        self._model = CrossEncoder(
            model_name, default_activation_function=torch.nn.Identity()
        )

    def rerank(self, query, documents):
        """Retorna um score 0-1 por documento, na mesma ordem da entrada."""
        if not documents:
            return []
        raw = self._model.predict([(query, doc) for doc in documents])
        return [1.0 / (1.0 + math.exp(-float(x))) for x in raw]
