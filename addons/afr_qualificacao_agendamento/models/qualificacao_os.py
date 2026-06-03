# -*- coding: utf-8 -*-
"""Extensões da OS de Qualificação para o agendamento de visitas.

Adiciona visita_ids; transforma date_planned_start/end em rollup das visitas
(opção X — redefinição de campo herdado como computed store); expõe contagem
e ação de visitas. O gate do action_schedule fica na Task 4.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AfrQualificacaoOs(models.Model):
    _inherit = "afr.qualificacao.os"

    visita_ids = fields.One2many(
        "afr.qualificacao.os.visita", "os_id", string="Visitas"
    )
    visita_count = fields.Integer(
        string="Nº de visitas", compute="_compute_visita_count"
    )

    # Opção X: rollup — redefine campos herdados como computed store.
    date_planned_start = fields.Datetime(
        compute="_compute_planned_dates_rollup",
        store=True,
        readonly=True,
        tracking=True,
    )
    date_planned_end = fields.Datetime(
        compute="_compute_planned_dates_rollup",
        store=True,
        readonly=True,
        tracking=True,
    )

    @api.depends("visita_ids.date_start", "visita_ids.date_stop")
    def _compute_planned_dates_rollup(self):
        for r in self:
            starts = [d for d in r.visita_ids.mapped("date_start") if d]
            stops = [d for d in r.visita_ids.mapped("date_stop") if d]
            if starts:
                r.date_planned_start = min(starts)
                r.date_planned_end = max(stops) if stops else False
            else:
                # Sem visitas: preserva valor escrito manualmente/por create()
                # (stored compute exige atribuição em todo branch → reatribui o atual).
                r.date_planned_start = r.date_planned_start
                r.date_planned_end = r.date_planned_end

    @api.depends("visita_ids")
    def _compute_visita_count(self):
        for r in self:
            r.visita_count = len(r.visita_ids)

    def action_schedule(self):
        for r in self:
            if (
                r.state == "draft"
                and r.qualificacao_ids
                and not r.visita_ids
                and not r.date_planned_start
            ):
                raise UserError(_(
                    "Adicione pelo menos uma visita para preencher as datas "
                    "planejadas antes de agendar a OS."
                ))
        return super().action_schedule()

    def action_view_visitas(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Visitas",
            "res_model": "afr.qualificacao.os.visita",
            "view_mode": "calendar,tree,form",
            "domain": [("os_id", "=", self.id)],
            "context": {
                "default_os_id": self.id,
                "default_tecnico_id": self.tecnico_default_id.id,
            },
        }
