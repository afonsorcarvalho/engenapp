{
    "name": "AFR Brasil Lookup",
    "version": "16.0.1.0.0",
    "category": "Tools",
    "license": "LGPL-3",
    "author": "AFR Sistemas",
    "website": "https://www.afrsistemas.com.br",
    "summary": "Preenche endereço por CEP (BrasilAPI) e dados de empresa por CNPJ (open.cnpja.com) em res.partner.",
    "description": """
AFR Brasil Lookup
=================

Adiciona dois lookups públicos (sem auth) em res.partner:

* **Buscar CEP** — preenche street, street2, district (bairro), city, state_id,
  country_id a partir de um CEP. Fonte: https://brasilapi.com.br/api/cep/v2/{CEP}.
* **Buscar CNPJ** — preenche razão social, nome fantasia, IE, endereço,
  telefone, e-mail a partir de um CNPJ. Fonte: https://open.cnpja.com/office/{CNPJ}.

Triggers:
* Botão "Buscar CEP"/"Buscar CNPJ" no formulário de res.partner (sempre).
* Onchange automático opcional (Configurações > Geral > AFR Brasil Lookup):
  ICPs `afr_brasil_lookup.auto_fill_cep` e `afr_brasil_lookup.auto_fill_cnpj`.

Tratamento de erros: timeout (5s), 404 (CEP/CNPJ não encontrado),
429 (rate limit). HTTP via stdlib (urllib.request), sem deps externas.
""",
    "depends": ["base", "contacts"],
    "data": [
        "data/ir_config_parameter.xml",
        "views/res_partner_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
