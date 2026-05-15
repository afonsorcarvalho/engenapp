# -*- coding: utf-8 -*-
{
    'name': 'Assistente LLM (LM Studio / Claude)',
    'version': '16.0.2.0.0',
    'category': 'Tools',
    'summary': 'Chat com LLM (LM Studio OpenAI-compat ou Anthropic Claude) acessível pelo systray.',
    'description': """
        Integração com provedor LLM configurável:

        * lmstudio (padrão): servidor OpenAI-compatible local (LM Studio,
          vLLM, Ollama). Em Docker, a URL base deve apontar para o host
          (ex.: http://host.docker.internal:1234/v1), pois localhost dentro
          do container não é a máquina onde o LM Studio escuta.
        * anthropic: API nativa Claude (POST https://api.anthropic.com/v1/messages,
          header x-api-key + anthropic-version). Modelos suportados incluem
          claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5-20251001.

        Inclui assistente no systray do backend, sessões de chat persistidas e
        consulta opcional a registros do Odoo mediante modelo e domínio
        permitidos nas configurações.
    """,
    'author': 'AFR Sistemas',
    'license': 'LGPL-3',
    'depends': ['web', 'base'],
    'data': [
        'security/ir.model.access.csv',
        'security/llm_assistant_security.xml',
        'data/llm_assistant_default_config.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'afr_llm_assistant/static/src/scss/llm_systray.scss',
            'afr_llm_assistant/static/src/xml/llm_systray.xml',
            'afr_llm_assistant/static/src/js/llm_systray.js',
        ],
    },
    'installable': True,
    'application': False,
}
