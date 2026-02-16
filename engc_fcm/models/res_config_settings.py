# -*- coding: utf-8 -*-
"""
Configuração do FCM (Service Account) em Configurações gerais.
Os parâmetros são armazenados em ir.config_parameter.
"""
import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fcm_service_account_path = fields.Char(
        string='Caminho do arquivo Service Account (JSON)',
        config_parameter='engc_fcm.service_account_path',
        help='Caminho no servidor para o arquivo JSON do Service Account do Firebase. '
             'Alternativa: use o parâmetro engc_fcm.service_account_json (JSON em texto) ou '
             'a variável de ambiente GOOGLE_APPLICATION_CREDENTIALS.'
    )
    fcm_service_account_json = fields.Text(
        string='Service Account JSON (conteúdo)',
        help='Conteúdo completo do JSON do Service Account. Se preenchido, tem prioridade sobre o caminho. '
             'Mantenha em segredo; use preferencialmente o caminho ou variável de ambiente.'
    )
    fcm_project_id = fields.Char(
        string='Firebase Project ID',
        config_parameter='engc_fcm.project_id',
        help='ID do projeto Firebase. Opcional se o JSON do Service Account já contiver project_id.'
    )

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfig = self.env['ir.config_parameter'].sudo()
        res['fcm_service_account_json'] = IrConfig.get_param('engc_fcm.service_account_json', default='')
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrConfig = self.env['ir.config_parameter'].sudo()
        json_val = self.fcm_service_account_json or ''
        IrConfig.set_param('engc_fcm.service_account_json', json_val)
        if json_val:
            _logger.info("FCM: configuração salva (Service Account JSON com %s caracteres).", len(json_val))
        else:
            _logger.info("FCM: conteúdo do JSON foi limpo (configuração removida).")
