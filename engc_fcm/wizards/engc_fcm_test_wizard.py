# -*- coding: utf-8 -*-
"""
Wizard para enviar uma notificação FCM de teste.
Permite escolher o usuário (com fcm_token) que receberá a notificação.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class EngcFcmTestWizard(models.TransientModel):
    _name = 'engc.fcm.test.wizard'
    _description = 'Enviar notificação FCM de teste'

    user_id = fields.Many2one(
        'res.users',
        string='Enviar para usuário',
        help='Usuário que receberá a notificação de teste (deve ter token FCM registrado). '
             'Deixe vazio para usar o seu próprio token.',
        domain="[('fcm_token', '!=', False), ('active', '=', True)]",
    )

    state = fields.Selection(
        [('draft', 'Rascunho'), ('sent', 'Enviado'), ('error', 'Erro')],
        default='draft',
        readonly=True,
    )
    result_message = fields.Text(readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Sugerir o usuário atual se tiver token
        if self.env.user.fcm_token and 'user_id' in fields_list:
            res['user_id'] = self.env.user.id
        return res

    def action_send_test(self):
        """Envia uma notificação FCM de teste para o usuário selecionado ou atual."""
        self.ensure_one()
        user = self.user_id or self.env.user
        if not user.fcm_token:
            raise UserError(
                _('O usuário "%s" não possui token FCM registrado. '
                  'Registre o token pelo app mobile após o login.') % user.name
            )

        from ..models import fcm_client
        # Payload no mesmo formato que o app espera (new_request_service)
        data = {
            'type': 'new_request_service',
            'request_service_id': '0',  # ID de teste
            'title': _('Teste FCM'),
            'body': _('Notificação de teste enviada pelo Odoo.'),
        }
        success = fcm_client.send_fcm_data_message(self.env, user.fcm_token, data)
        if success:
            self.write({
                'state': 'sent',
                'result_message': _(
                    'Notificação de teste enviada com sucesso para %s.\n\n'
                    'Se não apareceu no dispositivo: com o app em primeiro plano, mensagens só de "data" '
                    'não são exibidas automaticamente — o app Flutter deve tratar onMessage e mostrar '
                    'uma notificação local. Em segundo plano normalmente o sistema exibe.'
                ) % user.name,
            })
            _logger.info("FCM teste enviado para user_id=%s (login=%s)", user.id, user.login)
        else:
            self.write({
                'state': 'error',
                'result_message': _(
                    'Falha ao enviar. Verifique: (1) Configurações FCM (Service Account) em Configurações > Geral > Push (FCM); '
                    '(2) token do usuário ainda válido; (3) logs do servidor.'
                ),
            })
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
