# -*- coding: utf-8 -*-
"""
Estende engc.os (Ordem de Serviço) para enviar notificação push FCM ao criar e ao alterar status.
Inclui data programada (date_scheduled) e, ao concluir, data de término (date_finish).
"""
from odoo import api, models, _
import logging

_logger = logging.getLogger(__name__)

FCM_DATA_TYPE_NEW_OS = 'new_os'
FCM_DATA_TYPE_OS_UPDATED = 'os_updated'

OS_STATE_LABELS = {
    'draft': 'Criada',
    'under_budget': 'Em Orçamento',
    'pause_budget': 'Orçamento Pausado',
    'wait_authorization': 'Esperando aprovação',
    'wait_parts': 'Esperando peças',
    'execution_ready': 'Pronta para Execução',
    'under_repair': 'Em execução',
    'pause_repair': 'Execução Pausada',
    'reproved': 'Reprovada',
    'done': 'Concluída',
    'cancel': 'Cancelada',
}


from . import fcm_client


class EngcOs(models.Model):
    _inherit = 'engc.os'

    def _get_fcm_users_os(self):
        """Usuários que recebem push de Ordem de Serviço (grupo group_fcm_os_notify)."""
        self.ensure_one()
        group = self.env.ref('engc_fcm.group_fcm_os_notify', raise_if_not_found=False)
        if not group:
            return self.env['res.users']
        return self.env['res.users'].sudo().search([
            ('fcm_token', '!=', False),
            ('fcm_token', '!=', ''),
            ('active', '=', True),
            ('id', 'in', group.users.ids),
        ])

    def _send_fcm_os_to_users(self, data_or_builder):
        """
        Envia notificação FCM para usuários do grupo OS.
        data_or_builder: dict (mesmo para todos) ou callable(user) que retorna o dict (datas no fuso do usuário).
        """
        users = self._get_fcm_users_os()
        if not users:
            _logger.info("FCM: nenhum usuário elegível para push de OS (id=%s).", self.id)
            return
        for user in users:
            if not getattr(user, 'fcm_token', False):
                continue
            payload = data_or_builder(user) if callable(data_or_builder) else data_or_builder
            success, _ = fcm_client.send_fcm_data_message(self.env, user.fcm_token, payload)
            if success:
                _logger.info("FCM: push OS enviado para user_id=%s (%s) | OS id=%s", user.id, user.login, self.id)
            else:
                _logger.warning("FCM: push OS não enviado para user_id=%s (%s)", user.id, user.login)

    @api.model_create_multi
    def create(self, vals_list):
        result = super(EngcOs, self).create(vals_list)
        for record in result:
            try:
                _logger.info("FCM: nova Ordem de Serviço criada (id=%s), disparando push.", record.id)
                title = _('Nova Ordem de Serviço')

                def build_data(user):
                    body = record.name or str(record.id)
                    if record.date_scheduled:
                        body += '. Programada: %s' % fcm_client.format_datetime_for_fcm(record, record.date_scheduled, user=user)
                    data = {
                        'type': FCM_DATA_TYPE_NEW_OS,
                        'os_id': str(record.id),
                        'title': title,
                        'body': body,
                    }
                    if record.date_scheduled:
                        data['schedule_date'] = fcm_client.format_datetime_for_fcm(record, record.date_scheduled, user=user)
                    return data

                record._send_fcm_os_to_users(build_data)
            except Exception as e:
                _logger.warning("FCM: falha ao enviar push para nova OS id=%s: %s", record.id, e, exc_info=True)
        return result

    def write(self, vals):
        result = super(EngcOs, self).write(vals)
        if 'state' not in vals:
            return result
        new_state = vals.get('state')
        state_label = OS_STATE_LABELS.get(new_state, new_state or '')
        for record in self:
            try:
                title = _('Ordem de Serviço: status atualizado')
                body_base = '%s - %s' % (record.name or record.id, state_label)
                close_date = record.date_finish if (new_state == 'done' and record.date_finish) else None

                def build_data(user):
                    body = body_base
                    if close_date:
                        body += '. Data conclusão: %s' % fcm_client.format_datetime_for_fcm(record, close_date, user=user)
                    data = {
                        'type': FCM_DATA_TYPE_OS_UPDATED,
                        'os_id': str(record.id),
                        'title': title,
                        'body': body,
                        'event_type': 'status',
                        'state': new_state or '',
                    }
                    if close_date:
                        data['close_date'] = fcm_client.format_datetime_for_fcm(record, close_date, user=user)
                    return data

                record._send_fcm_os_to_users(build_data)
            except Exception as e:
                _logger.warning("FCM: falha ao enviar push de atualização OS id=%s: %s", record.id, e, exc_info=True)
        return result
