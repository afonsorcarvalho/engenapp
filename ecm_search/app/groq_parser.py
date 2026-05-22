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

_PROMPT = """Você é um assistente de busca de documentos empresariais brasileiros.
Dada a query de busca do usuário, extraia metadados em JSON para refinar a busca.

Query: "__QUERY__"

Regras:
- "tipo_documento": APENAS se a query indicar claramente o tipo. Um de:
  "nota_fiscal", "contrato", "laudo", "relatorio". Caso contrário, null.
  Nunca retorne "outro".
- "mes" / "ano": número, somente se a query mencionar um período. Senão null.
- "keywords_adicionais": termos de busca ADICIONAIS e ESPECÍFICOS — sinônimos,
  siglas ou expansões que ajudem a localizar o documento e que NÃO apareçam
  na query. NÃO repita palavras da query. NÃO inclua palavras genéricas
  (documento, arquivo, informação, dado, coisa, item, conteúdo, texto).
  Se não houver termo específico a acrescentar, retorne lista vazia.
- "entidades": nomes próprios de empresas ou pessoas mencionados na query.

Exemplos:
Query: "carteira de habilitação do João"
JSON: {"tipo_documento": null, "mes": null, "ano": null, "keywords_adicionais": ["CNH", "carteira nacional de habilitação", "permissão para dirigir"], "entidades": ["João"]}

Query: "notas fiscais de compra de março de 2025"
JSON: {"tipo_documento": "nota_fiscal", "mes": 3, "ano": 2025, "keywords_adicionais": ["NF", "fatura", "entrada"], "entidades": []}

Query: "algum documento sobre a empresa XYZ"
JSON: {"tipo_documento": null, "mes": null, "ano": null, "keywords_adicionais": [], "entidades": ["XYZ"]}

Retorne APENAS o JSON, sem markdown, sem explicação."""


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
                "messages": [
                    {"role": "user", "content": _PROMPT.replace("__QUERY__", query)}
                ],
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
