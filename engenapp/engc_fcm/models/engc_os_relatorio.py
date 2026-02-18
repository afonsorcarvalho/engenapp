# -*- coding: utf-8 -*-
"""
Estende engc.os.relatorios (Relatório de Atendimento) para enviar notificação push FCM
ao criar e ao alterar status. Inclui data de atendimento e, ao concluir, data de conclusão.
"""
from odoo import api, models, _
import logging

_logger = logging.getLogger(__name__)

FCM_DATA_TYPE_NEW_RELATORIO_ATENDIMENTO = 'new_relatorio_atendimento'
FCM_DATA_TYPE_RELATORIO_ATENDIMENTO_UPDATED = 'relatorio_atendimento_updated'

RELATORIO_STATE_LABELS = {
    'draft': 'Criado',
    'done': 'Concluído',
    'cancel': 'Cancelado',
}


from . import fcm_client


class EngcOsRelatorios(models.Model):
    _inherit = 'engc.os.relatorios'

    def _get_fcm_users_relatorio(self):
        """Usuários que recebem push de Relatório de Atendimento (grupo group_fcm_relatorio_atendimento_notify)."""
        self.ensure_one()
        group = self.env.ref('engc_fcm.group_fcm_relatorio_atendimento_notify', raise_if_not_found=False)
        if not group:
            return self.env['res.users']
        return self.env['res.users'].sudo().search([
            ('fcm_token', '!=', False),
            ('fcm_token', '!=', ''),
            ('active', '=', True),
            ('id', 'in', group.users.ids),
        ])

    def _send_fcm_relatorio_to_users(self, data_or_builder):
        """
        Envia notificação FCM para usuários do grupo Relatório de Atendimento.
        data_or_builder: dict ou callable(user) que retorna o dict (datas no fuso do usuário).
        """
        users = self._get_fcm_users_relatorio()
        if not users:
            _logger.info("FCM: nenhum usuário elegível para push de Relatório (id=%s).", self.id)
            return
        for user in users:
            if not getattr(user, 'fcm_token', False):
                continue
            payload = data_or_builder(user) if callable(data_or_builder) else data_or_builder
            success, _ = fcm_client.send_fcm_data_message(self.env, user.fcm_token, payload)
            if success:
                _logger.info("FCM: push Relatório enviado para user_id=%s (%s) | Relatório id=%s", user.id, user.login, self.id)
            else:
                _logger.warning("FCM: push Relatório não enviado para user_id=%s (%s)", user.id, user.login)

    @api.model_create_multi
    def create(self, vals_list):
        result = super(EngcOsRelatorios, self).create(vals_list)
        for record in result:
            try:
                _logger.info("FCM: novo Relatório de Atendimento criado (id=%s), disparando push.", record.id)
                os_name = record.os_id.name if record.os_id else '-'
                title = _('Novo Relatório de Atendimento')

                def build_data(user):
                    body = '%s (OS: %s)' % (record.name or record.id, os_name)
                    if record.data_atendimento:
                        body += '. Atendimento: %s' % fcm_client.format_datetime_for_fcm(record, record.data_atendimento, user=user)
                    data = {
                        'type': FCM_DATA_TYPE_NEW_RELATORIO_ATENDIMENTO,
                        'relatorio_id': str(record.id),
                        'os_id': str(record.os_id.id) if record.os_id else '',
                        'title': title,
                        'body': body,
                    }
                    if record.data_atendimento:
                        data['data_atendimento'] = fcm_client.format_datetime_for_fcm(record, record.data_atendimento, user=user)
                    if record.data_fim_atendimento:
                        data['data_fim_atendimento'] = fcm_client.format_datetime_for_fcm(record, record.data_fim_atendimento, user=user)
                    return data

                record._send_fcm_relatorio_to_users(build_data)
            except Exception as e:
                _logger.warning("FCM: falha ao enviar push para novo Relatório id=%s: %s", record.id, e, exc_info=True)
        return result

    def write(self, vals):
        result = super(EngcOsRelatorios, self).write(vals)
        if 'state' not in vals:
            return result
        new_state = vals.get('state')
        state_label = RELATORIO_STATE_LABELS.get(new_state, new_state or '')
        for record in self:
            try:
                os_name = record.os_id.name if record.os_id else '-'
                title = _('Relatório de Atendimento: status atualizado')
                body_base = '%s (OS: %s) - %s' % (record.name or record.id, os_name, state_label)
                close_date = record.data_fim_atendimento if (new_state == 'done' and record.data_fim_atendimento) else None

                def build_data(user):
                    body = body_base
                    if close_date:
                        body += '. Data conclusão: %s' % fcm_client.format_datetime_for_fcm(record, close_date, user=user)
                    data = {
                        'type': FCM_DATA_TYPE_RELATORIO_ATENDIMENTO_UPDATED,
                        'relatorio_id': str(record.id),
                        'os_id': str(record.os_id.id) if record.os_id else '',
                        'title': title,
                        'body': body,
                        'event_type': 'status',
                        'state': new_state or '',
                    }
                    if close_date:
                        data['close_date'] = fcm_client.format_datetime_for_fcm(record, close_date, user=user)
                    return data

                record._send_fcm_relatorio_to_users(build_data)
            except Exception as e:
                _logger.warning("FCM: falha ao enviar push de atualização Relatório id=%s: %s", record.id, e, exc_info=True)
        return result
