# -*- coding: utf-8 -*-
"""
Estende engc.request.service para enviar notificação push FCM ao criar uma nova
Solicitação de Serviço. O payload data segue o contrato do app Flutter:
type, request_service_id, title, body.
"""
from odoo import api, models, _
import logging

from . import fcm_client

_logger = logging.getLogger(__name__)

# Tipos de mensagem esperados pelo app Flutter
FCM_DATA_TYPE_NEW_REQUEST_SERVICE = 'new_request_service'
FCM_DATA_TYPE_REQUEST_SERVICE_UPDATED = 'request_service_updated'

# Labels de estado para o body da notificação
STATE_LABELS = {
    'new': 'Nova Solicitação',
    'in_progress': 'Em andamento',
    'done': 'Concluído',
    'cancel': 'Cancelada',
}


class RequestService(models.Model):
    _inherit = 'engc.request.service'

    def write(self, vals):
        """Envia push FCM quando houver alteração de técnico ou de status."""
        result = super(RequestService, self).write(vals)
        for record in self:
            try:
                if 'tecnicos' in vals:
                    _logger.info(
                        "FCM: técnico alterado na Solicitação de Serviço id=%s, disparando push.",
                        record.id,
                    )
                    record._send_fcm_request_service_updated(
                        event_type='technician',
                        title=_('Solicitação de Serviço: técnico alterado'),
                        body_base=record.name or str(record.id),
                    )
                if 'state' in vals:
                    new_state = vals.get('state')
                    state_label = STATE_LABELS.get(new_state, new_state or '')
                    body_base = '%s - %s' % (record.name or record.id, state_label)
                    _logger.info(
                        "FCM: status alterado na Solicitação de Serviço id=%s para %s, disparando push.",
                        record.id,
                        state_label,
                    )
                    record._send_fcm_request_service_updated(
                        event_type='status',
                        title=_('Solicitação de Serviço: status atualizado'),
                        body_base=body_base,
                        new_state=new_state,
                        close_date=record.close_date if new_state == 'done' else None,
                    )
            except Exception as e:
                _logger.warning(
                    "FCM: falha ao enviar notificação de atualização para Solicitação de Serviço ID %s: %s",
                    record.id,
                    e,
                    exc_info=True,
                )
        return result

    @api.model_create_multi
    def create(self, vals_list):
        result = super(RequestService, self).create(vals_list)
        for record in result:
            try:
                _logger.info(
                    "FCM: nova Solicitação de Serviço criada (id=%s), disparando push para usuários do grupo.",
                    record.id,
                )
                self._send_fcm_new_request_service(record)
            except Exception as e:
                # Não quebrar o create em caso de falha no envio FCM
                _logger.warning(
                    "FCM: falha ao enviar notificação para nova Solicitação de Serviço ID %s: %s",
                    record.id, e, exc_info=True
                )
        return result

    def _get_fcm_users(self):
        """
        Retorna usuários ativos com fcm_token preenchido que estejam no grupo de notificação.
        """
        self.ensure_one()
        group = self.env.ref('engc_fcm.group_fcm_request_service_notify', raise_if_not_found=False)
        if not group:
            _logger.info(
                "FCM: grupo engc_fcm.group_fcm_request_service_notify não encontrado; nenhum usuário notificado.")
            return self.env['res.users']
        user_domain = [
            ('fcm_token', '!=', False),
            ('fcm_token', '!=', ''),
            ('active', '=', True),
            ('id', 'in', group.users.ids),
        ]
        users = self.env['res.users'].sudo().search(user_domain)
        _logger.info(
            "FCM: usuários elegíveis para push (Solicitação de Serviço): %s (ids=%s)",
            len(users),
            users.ids,
        )
        return users

    def _send_fcm_to_users(self, users, data, record_id=None, action="novo", extra=None):
        """
        Envia notificação FCM para cada usuário do grupo.
        data pode ser um dict (mesmo payload para todos) ou um callable data(user) que retorna
        o dict por destinatário (para datas no fuso de cada usuário).
        """
        if not users:
            _logger.info("FCM: nenhum usuário elegível para notificar (Solicitação de Serviço id=%s).", record_id or getattr(self, 'id', '-'))
            return

        for user in users:
            if not getattr(user, 'fcm_token', False):
                continue
            payload = data(user) if callable(data) else data
            success, detail = fcm_client.send_fcm_data_message(self.env, user.fcm_token, payload)
            if success:
                msg = "FCM: push{}{} enviado para user_id={} ({}) | Solicitação id={}".format(
                    " (atualização)" if action == "update" else "",
                    f" ({extra})" if extra else "",
                    user.id,
                    getattr(user, 'login', '-'),
                    record_id or getattr(self, 'id', '-'),
                )
                _logger.info(msg)
            else:
                _logger.warning(
                    "FCM: push{}{} não enviado para user_id=%s (%s): %s".format(
                        " (atualização)" if action == "update" else "",
                        f" ({extra})" if extra else "",
                    ),
                    user.id, getattr(user, 'login', '-'), detail or "erro desconhecido"
                )

    def _send_fcm_new_request_service(self, record):
        """
        Envia mensagem FCM de nova solicitação.
        Data programada no body e no payload é formatada no fuso de cada destinatário.
        """
        users = record._get_fcm_users()
        title = _('Nova Solicitação de Serviço')

        def build_data(user):
            body = record.name or str(record.id)
            if record.schedule_date:
                body += '. Programada: %s' % fcm_client.format_datetime_for_fcm(record, record.schedule_date, user=user)
            data = {
                'type': FCM_DATA_TYPE_NEW_REQUEST_SERVICE,
                'request_service_id': str(record.id),
                'title': title,
                'body': body,
            }
            if record.schedule_date:
                data['schedule_date'] = fcm_client.format_datetime_for_fcm(record, record.schedule_date, user=user)
            return data

        _logger.info(
            "FCM: enviando push para %s usuário(s) | Solicitação de Serviço id=%s name=%s",
            len(users),
            record.id,
            record.name or "-",
        )
        record._send_fcm_to_users(users, build_data, record_id=record.id)

    def _send_fcm_request_service_updated(self, event_type, title, body_base, new_state=None, close_date=None):
        """
        Envia mensagem FCM de atualização de solicitação.
        body_base não deve incluir data de conclusão; close_date é formatada no fuso de cada destinatário.
        """
        self.ensure_one()
        users = self._get_fcm_users()

        def build_data(user):
            body = body_base
            if close_date:
                body += '. Data conclusão: %s' % fcm_client.format_datetime_for_fcm(self, close_date, user=user)
            data = {
                'type': FCM_DATA_TYPE_REQUEST_SERVICE_UPDATED,
                'request_service_id': str(self.id),
                'title': title,
                'body': body,
                'event_type': event_type,
            }
            if new_state is not None:
                data['state'] = new_state
            if close_date:
                data['close_date'] = fcm_client.format_datetime_for_fcm(self, close_date, user=user)
            return data

        _logger.info(
            "FCM: enviando push de atualização para %s usuário(s) | Solicitação id=%s event_type=%s",
            len(users),
            self.id,
            event_type,
        )
        self._send_fcm_to_users(users, build_data, record_id=self.id, action="update", extra=event_type)
