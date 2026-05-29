from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    brl_auto_fill_cep = fields.Boolean(
        string="Preencher endereço ao digitar CEP",
        config_parameter="afr_brasil_lookup.auto_fill_cep",
        help="Quando ativado, sair do campo CEP em res.partner dispara a busca "
             "automática em BrasilAPI e preenche endereço.",
    )
    brl_auto_fill_cnpj = fields.Boolean(
        string="Preencher empresa ao digitar CNPJ",
        config_parameter="afr_brasil_lookup.auto_fill_cnpj",
        help="Quando ativado, sair do campo CNPJ (vat) em res.partner dispara "
             "a busca automática em open.cnpja.com e preenche dados.",
    )
