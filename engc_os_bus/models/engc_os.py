# -*- coding: utf-8 -*-
"""Estende engc.os para emitir eventos no bus.bus em create/write.

O frontend web (Next.js) faz longpolling em /longpolling/poll subscrito ao
canal 'engc.os' e usa as mensagens para invalidar caches e atualizar UI.
"""
from odoo import api, models
import logging

_logger = logging.getLogger(__name__)

BUS_CHANNEL = 'engc.os'
BUS_NOTIFICATION_TYPE = 'engc_os.changed'


class EngcOs(models.Model):
    _inherit = 'engc.os'

    def _notify_bus_change(self, event):
        if not self:
            return
        bus_bus = self.env['bus.bus'].sudo()
        for rec in self:
            payload = {
                'event': event,
                'id': rec.id,
                'name': rec.name or '',
                'state': rec.state or '',
                'write_date': rec.write_date.isoformat() if rec.write_date else '',
            }
            try:
                bus_bus._sendone(BUS_CHANNEL, BUS_NOTIFICATION_TYPE, payload)
            except Exception as e:
                _logger.warning("bus.bus: falha ao notificar OS id=%s: %s", rec.id, e)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._notify_bus_change('created')
        return records

    def write(self, vals):
        result = super().write(vals)
        if vals:
            self._notify_bus_change('updated')
        return result
