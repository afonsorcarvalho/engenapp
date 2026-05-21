import json

import requests

EMPTY = {
    "tipo_documento": None,
    "mes": None,
    "ano": None,
    "keywords_adicionais": [],
    "entidades": [],
}

_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

_PROMPT = """Você é um sistema de busca de documentos empresariais brasileiros.
Analise a query do usuário e extraia as informações em JSON.

Query: "{query}"

Retorne APENAS um JSON válido (sem explicações, sem markdown) com os campos:
{{
  "tipo_documento": "nota_fiscal | contrato | laudo | relatorio | outro | null",
  "mes": <number ou null>,
  "ano": <number ou null>,
  "keywords_adicionais": ["termos", "relevantes"],
  "entidades": ["nomes de empresas ou pessoas"]
}}"""


def parse_query(query, api_key, model, endpoint=_ENDPOINT):
    """Parse a natural-language query via Groq. Falls back to EMPTY on failure."""
    try:
        resp = requests.post(
            endpoint,
            timeout=30,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "temperature": 0,
                "max_tokens": 300,
                "messages": [{"role": "user", "content": _PROMPT.format(query=query)}],
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
    except (requests.RequestException, KeyError, ValueError, TypeError):
        return dict(EMPTY)
    if not isinstance(data, dict):
        return dict(EMPTY)
    return {**EMPTY, **{k: data.get(k, EMPTY[k]) for k in EMPTY}}
