import json
from unittest.mock import patch, MagicMock

from app.groq_parser import parse_query, EMPTY


def _mock_resp(content):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    return resp


def test_parse_ok():
    payload = json.dumps({
        "tipo_documento": "nota_fiscal", "mes": 3, "ano": 2025,
        "keywords_adicionais": ["compra"], "entidades": ["XYZ"],
    })
    with patch("app.groq_parser.requests.post", return_value=_mock_resp(payload)):
        result = parse_query("nf de compra 03/2025", "key", "model")
    assert result["tipo_documento"] == "nota_fiscal"
    assert result["mes"] == 3 and result["ano"] == 2025
    assert result["keywords_adicionais"] == ["compra"]
    assert result["entidades"] == ["XYZ"]


def test_parse_invalid_json_falls_back():
    with patch("app.groq_parser.requests.post",
               return_value=_mock_resp("desculpe, nao sei")):
        result = parse_query("query qualquer", "key", "model")
    assert result == EMPTY


def test_parse_request_error_falls_back():
    import requests
    with patch("app.groq_parser.requests.post",
               side_effect=requests.RequestException("boom")):
        result = parse_query("query qualquer", "key", "model")
    assert result == EMPTY


def test_parse_non_object_json_falls_back():
    # valid JSON but not an object: json.loads succeeds, data.get must not crash
    for content in ("null", "[]", '"texto"', "42"):
        with patch("app.groq_parser.requests.post",
                   return_value=_mock_resp(content)):
            result = parse_query("query qualquer", "key", "model")
        assert result == EMPTY


def test_parse_keeps_only_known_keys():
    payload = json.dumps({"tipo_documento": "contrato", "lixo": "ignora"})
    with patch("app.groq_parser.requests.post", return_value=_mock_resp(payload)):
        result = parse_query("contrato", "key", "model")
    assert "lixo" not in result
    assert result["tipo_documento"] == "contrato"
