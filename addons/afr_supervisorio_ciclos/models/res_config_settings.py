from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    public_key = fields.Char(
        string='Chave Pública',
        help='Chave pública para verificação de assinatura digital das fitas (em base64)',
        config_parameter='afr_supervisorio_ciclos.public_key'
    )
    public_key_filename = fields.Char(
        string='Nome do Arquivo da Chave Pública'
    ) 