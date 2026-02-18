# -*- coding: utf-8 -*-
"""
Herda calendar.event para:
- Exigir grupo Gestor PCM para alterar/excluir eventos vinculados a OS.
- Atualizar a OS (date_scheduled e estimated_execution_duration) quando a data/hora
  do evento for alterada na agenda.
"""

from odoo import models, _
from odoo.exceptions import AccessError, ValidationError


# Estados da OS em que o evento da agenda pode ser alterado
OS_STATES_ALLOW_CALENDAR_EDIT = ('draft', 'execution_ready','under_repair')


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    def _linked_to_engc_os(self):
        """Retorna True se o evento estiver vinculado a uma Ordem de Serviço."""
        return self.res_model == 'engc.os' and self.res_id

    def _check_gestor_pcm_for_os_events(self):
        """
        Levanta AccessError se algum evento estiver vinculado a OS e o usuário
        não pertencer ao grupo Gestor PCM.
        """
        if self.filtered(lambda e: e._linked_to_engc_os()):
            if not self.env.user.has_group('engc_os.group_gestor_pcm'):
                raise AccessError(
                    _('Apenas usuários do grupo "Gestor PCM" podem alterar ou excluir '
                      'eventos da agenda que estejam vinculados a Ordens de Serviço (OS).')
                )

    def _check_os_state_for_os_events(self):
        """
        Levanta ValidationError se algum evento vinculado a OS tiver a OS
        em estado que não permite alteração (apenas "Criada" ou "Pronta para Execução").
        """
        for event in self:
            if not event._linked_to_engc_os():
                continue
            os_record = self.env['engc.os'].browse(event.res_id).exists()
            if not os_record:
                continue
            if os_record.state not in OS_STATES_ALLOW_CALENDAR_EDIT:
                state_label = dict(os_record._fields['state'].selection).get(
                    os_record.state, os_record.state
                )
                raise ValidationError(
                    _('O evento da agenda só pode ser alterado quando a Ordem de Serviço '
                      'estiver com status "Criada" ou "Pronta para Execução". '
                      'A OS %s está com status "%s".') % (os_record.name, state_label)
                )

    def _update_os_from_calendar(self):
        """
        Atualiza a OS vinculada com a data programada e o tempo estimado
        quando start/stop do evento forem alterados.
        """
        for event in self:
            if not event._linked_to_engc_os():
                continue
            os_record = self.env['engc.os'].browse(event.res_id).exists()
            if not os_record:
                continue
            duration_hours = (event.stop - event.start).total_seconds() / 3600.0
            if duration_hours <= 0:
                duration_hours = 1.0
            os_record.with_context(engc_os_skip_calendar_sync=True).write({
                'date_scheduled': event.start,
                'estimated_execution_duration': duration_hours,
            })

    def write(self, vals):
        time_fields = {'start', 'stop', 'duration', 'start_date', 'stop_date'}
        time_updated = bool(time_fields & set(vals))
        # Verifica permissão e estado da OS antes de escrever (eventos vinculados a OS)
        self._check_gestor_pcm_for_os_events()
        self._check_os_state_for_os_events()
        result = super(CalendarEvent, self).write(vals)
        if time_updated:
            self._update_os_from_calendar()
        return result

    def unlink(self):
        self._check_gestor_pcm_for_os_events()
        self._check_os_state_for_os_events()
        return super(CalendarEvent, self).unlink()
