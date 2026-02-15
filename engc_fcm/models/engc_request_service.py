# -*- coding: utf-8 -*-
"""
Estende engc.request.service para enviar notificação push FCM ao criar uma nova
Solicitação de Serviço. O payload data segue o contrato do app Flutter:
type, request_service_id, title, body.
"""
from odoo import api, models, _
import logging

_logger = logging.getLogger(__name__)

# Tipo de mensagem esperado pelo app Flutter
FCM_DATA_TYPE_NEW_REQUEST_SERVICE = 'new_request_service'


class RequestService(models.Model):
    _inherit = 'engc.request.service'

    @api.model_create_multi
    def create(self, vals_list):
        result = super(RequestService, self).create(vals_list)
        for record in result:
            try:
                self._send_fcm_new_request_service(record)
            except Exception as e:
                # Não quebrar o create em caso de falha no envio FCM
                _logger.warning(
                    "FCM: falha ao enviar notificação para nova Solicitação de Serviço ID %s: %s",
                    record.id, e, exc_info=True
                )
        return result

    def _get_users_to_notify_new_request_service(self):
        """
        Retorna os usuários que devem receber push ao criar Solicitação de Serviço:
        usuários com fcm_token preenchido e que pertencem ao grupo de notificação
        (engc_fcm.group_fcm_request_service_notify).
        """
        self.ensure_one()
        group = self.env.ref('engc_fcm.group_fcm_request_service_notify', raise_if_not_found=False)
        if not group:
            return self.env['res.users']
        return self.env['res.users'].sudo().search([
            ('fcm_token', '!=', False),
            ('fcm_token', '!=', ''),
            ('active', '=', True),
            ('id', 'in', group.users.ids),
        ])

    def _send_fcm_new_request_service(self, record):
        """
        Envia mensagem FCM para usuários elegíveis com payload data no formato
        esperado pelo app: type, request_service_id, title, body.
        Disparado em: create do modelo engc.request.service (este módulo).
        """
        users = record._get_users_to_notify_new_request_service()
        if not users:
            return

        # Payload data exatamente como o app Flutter espera
        title = _('Nova Solicitação de Serviço')
        body = record.name or str(record.id)
        data = {
            'type': FCM_DATA_TYPE_NEW_REQUEST_SERVICE,
            'request_service_id': str(record.id),
            'title': title,
            'body': body,
        }

        from . import fcm_client
        for user in users:
            if not user.fcm_token:
                continue
            success = fcm_client.send_fcm_data_message(record.env, user.fcm_token, data)
            if not success:
                _logger.debug("FCM não enviado para user_id=%s (token pode ser inválido).", user.id)
