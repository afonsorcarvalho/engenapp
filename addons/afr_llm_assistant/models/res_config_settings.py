# -*- coding: utf-8 -*-
"""Parâmetros de conexão com provedor LLM (LM Studio OpenAI-compat ou Anthropic Claude)."""

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    afr_llm_provider = fields.Selection(
        [
            ('lmstudio', 'LM Studio / OpenAI-compatible (local)'),
            ('anthropic', 'Anthropic Claude (API nativa /v1/messages)'),
        ],
        string='Provedor LLM',
        config_parameter='afr_llm_assistant.provider',
        default='lmstudio',
        help='lmstudio: chama /v1/chat/completions (LM Studio, vLLM, Ollama OpenAI-compat). '
        'anthropic: chama https://api.anthropic.com/v1/messages com header x-api-key e '
        'anthropic-version. Para Claude defina também "Modelo" (ex.: claude-sonnet-4-6) e '
        '"Chave API" (sk-ant-...). URL base é ignorada quando provedor=anthropic.',
    )
    afr_llm_api_base_url = fields.Char(
        string='URL base da API (LM Studio)',
        config_parameter='afr_llm_assistant.api_base_url',
        help='Uma ou várias URLs (vírgula). Variáveis de ambiente (têm prioridade): ODOO_LMSTUDIO_API_BASE; '
        'opcionalmente ODOO_LMSTUDIO_HOST_LAN (IPv4 do host) e ODOO_LMSTUDIO_HOST_PORT (padrão 1234) para '
        'tentar antes as URLs derivadas do IP LAN. Ignorado quando provedor=anthropic.',
    )
    afr_llm_model = fields.Char(
        string='Nome do modelo',
        config_parameter='afr_llm_assistant.model',
        help='LM Studio: identificador como exibido (ex.: google/gemma-3-4b-it). '
        'Anthropic: id de modelo Claude (ex.: claude-opus-4-7, claude-sonnet-4-6, '
        'claude-haiku-4-5-20251001).',
    )
    afr_llm_api_key = fields.Char(
        string='Chave API',
        config_parameter='afr_llm_assistant.api_key',
        help='LM Studio: opcional. Anthropic: sk-ant-... obrigatório.',
    )
    afr_llm_anthropic_max_tokens = fields.Integer(
        string='Anthropic max_tokens',
        config_parameter='afr_llm_assistant.anthropic_max_tokens',
        default=4096,
        help='Limite de tokens de saída por chamada (obrigatório na API Anthropic). '
        'Padrão 4096. Subir só se o modelo precisar de respostas longas.',
    )
    afr_llm_anthropic_version = fields.Char(
        string='Anthropic-Version',
        config_parameter='afr_llm_assistant.anthropic_version',
        default='2023-06-01',
        help='Valor do header anthropic-version. Manter 2023-06-01 salvo motivo específico.',
    )
    afr_llm_whitelisted_models = fields.Char(
        string='Modelos Odoo permitidos para consulta',
        config_parameter='afr_llm_assistant.whitelisted_models',
        help='Lista separada por vírgulas de nomes técnicos de modelos que o assistente pode '
        'consultar via bloco ODOO_QUERY (ex.: afr.supervisorio.ciclos).',
    )
