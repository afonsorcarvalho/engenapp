# -*- coding: utf-8 -*-
"""Visita de campo de uma OS de Qualificação (afr.qualificacao.os.visita).

Unidade agendável = OS × dia × técnico. Fase A: modelo base, datetimes
computados para a calendar, e detecção de conflito de técnico/deslocamento
(avisos não-bloqueantes — Task 5).
"""
from datetime import datetime, time, timedelta

from pytz import timezone, utc

from odoo import _, api, fields, models


class AfrQualificacaoOsVisita(models.Model):
    _name = "afr.qualificacao.os.visita"
    _description = "Visita de OS de Qualificação"
    _order = "date, time_start, id"

    name = fields.Char(string="Visita", compute="_compute_name", store=True)
    os_id = fields.Many2one(
        "afr.qualificacao.os",
        string="OS de Qualificação",
        required=True,
        ondelete="cascade",
        index=True,
    )
    tecnico_id = fields.Many2one(
        "hr.employee",
        string="Técnico",
        required=True,
        index=True,
        help="Técnico desta visita. Editável para reatribuir grupos paralelos.",
    )
    date = fields.Date(string="Data", required=True, index=True)
    time_start = fields.Float(
        string="Hora início", help="Opcional. Vazio = início do dia (00:00)."
    )
    time_stop = fields.Float(
        string="Hora fim", help="Opcional. Vazio = fim do dia (23:59)."
    )
    date_start = fields.Datetime(
        string="Início",
        compute="_compute_datetimes",
        store=True,
        help="date + time_start convertido p/ UTC (fonte da calendar).",
    )
    date_stop = fields.Datetime(
        string="Fim", compute="_compute_datetimes", store=True
    )
    equipment_ids = fields.Many2many(
        "engc.equipment",
        string="Equipamentos",
        help="Equipamentos trabalhados nesta visita.",
    )
    planned_hours = fields.Float(
        string="Horas previstas",
        help="Horas de trabalho previstas no dia (≤ jornada do equipamento).",
    )
    travel_buffer_hours = fields.Float(
        string="Deslocamento (h)",
        help="Tempo de deslocamento até esta visita (manual).",
    )
    partner_id = fields.Many2one(
        related="os_id.partner_id", string="Cliente", store=True, readonly=True
    )
    city = fields.Char(
        related="partner_id.city", string="Cidade", store=True, readonly=True
    )
    company_id = fields.Many2one(
        related="os_id.company_id", store=True, readonly=True
    )
    sequence = fields.Integer(default=10)
    state = fields.Selection(
        [("planned", "Planejada"), ("done", "Realizada")],
        default="planned",
        required=True,
    )
    note = fields.Text(string="Observações")

    # Campos de conflito — implementados na Task 5
    tecnico_conflict = fields.Boolean(
        string="Conflito de técnico", compute="_compute_conflicts"
    )
    tecnico_conflict_msg = fields.Char(compute="_compute_conflicts")
    travel_conflict = fields.Boolean(
        string="Conflito de deslocamento", compute="_compute_conflicts"
    )
    travel_conflict_msg = fields.Char(compute="_compute_conflicts")

    # ───────── helpers ─────────
    def _local_to_utc(self, naive_dt):
        """Datetime naive local (tz do usuário) → naive UTC p/ armazenar."""
        tz = timezone(self.env.user.tz or "UTC")
        return tz.localize(naive_dt).astimezone(utc).replace(tzinfo=None)

    @api.depends("os_id.name", "date", "tecnico_id")
    def _compute_name(self):
        for r in self:
            parts = []
            if r.os_id.name:
                parts.append(r.os_id.name)
            if r.date:
                parts.append(fields.Date.to_string(r.date))
            if r.tecnico_id:
                parts.append(r.tecnico_id.name)
            r.name = " / ".join(parts) or _("Visita")

    @api.depends("date", "time_start", "time_stop")
    def _compute_datetimes(self):
        for r in self:
            if not r.date:
                r.date_start = r.date_stop = False
                continue
            base = datetime.combine(r.date, time.min)
            start_h = r.time_start or 0.0
            stop_h = r.time_stop if r.time_stop else 23.9833  # ~23:59
            r.date_start = r._local_to_utc(base + timedelta(hours=start_h))
            r.date_stop = r._local_to_utc(base + timedelta(hours=stop_h))

    @api.depends("tecnico_id", "date_start", "date_stop", "city",
                 "travel_buffer_hours")
    def _compute_conflicts(self):
        for r in self:
            r.tecnico_conflict = False
            r.tecnico_conflict_msg = False
            r.travel_conflict = False
            r.travel_conflict_msg = False
            if not r.tecnico_id or not r.date_start or not r.date_stop:
                continue
            exclude = [("id", "!=", r._origin.id)] if r._origin.id else []
            # Técnico em dois lugares: sobreposição de janela.
            overlap = self.search(exclude + [
                ("tecnico_id", "=", r.tecnico_id.id),
                ("date_start", "<", r.date_stop),
                ("date_stop", ">", r.date_start),
            ], limit=1)
            if overlap:
                r.tecnico_conflict = True
                r.tecnico_conflict_msg = _(
                    "%s já tem outra visita sobreposta: %s."
                ) % (r.tecnico_id.name, overlap.os_id.name or _("(sem OS)"))
            # Deslocamento: visita anterior do técnico em outra cidade.
            prev = self.search(exclude + [
                ("tecnico_id", "=", r.tecnico_id.id),
                ("date_stop", "<=", r.date_start),
                ("city", "!=", False),
            ], order="date_stop desc", limit=1)
            if prev and r.city and prev.city != r.city:
                gap_h = (r.date_start - prev.date_stop).total_seconds() / 3600.0
                need = r.travel_buffer_hours or 0.0
                if gap_h < need:
                    r.travel_conflict = True
                    r.travel_conflict_msg = _(
                        "Deslocamento %s → %s: %.1f h livres < %.1f h necessárias."
                    ) % (prev.city, r.city, gap_h, need)
