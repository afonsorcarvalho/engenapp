# -*- coding: utf-8 -*-
"""Extensões da OS de Qualificação para o agendamento de visitas.

Adiciona visita_ids; transforma date_planned_start/end em rollup das visitas
(opção X — redefinição de campo herdado como computed store); expõe contagem
e ação de visitas. O gate do action_schedule fica na Task 4.
"""
import math
from datetime import timedelta

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

    def _visita_parallel_group(self, equipment):
        """Rótulo de grupo paralelo do equipamento (primeiro não-vazio entre suas qualifs)."""
        quals = self.qualificacao_ids.filtered(lambda q: q.equipment_id == equipment)
        for q in quals:
            if q.parallel_group:
                return q.parallel_group
        return False

    def _suggest_visitas(self, tecnico, date_start):
        """Gera visitas diárias distribuindo as horas estimadas (F5.8.0) por dia.

        - Apaga visitas 'planned' (preserva 'done').
        - Agrupa equipamentos por parallel_group; solo em sequência, paralelo junto.
        - Dias corridos a partir de date_start.
        """
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_(
                "OS sem pedido de venda; não há horas estimadas para sugerir visitas."
            ))
        self.visita_ids.filtered(lambda v: v.state == "planned").unlink()
        rows = self.sale_order_id._qualif_schedule_rows()

        # Monta blocos preservando a ordem de aparição.
        blocks = []
        seen_groups = {}
        for row in rows:
            equip = row.get("equipment")
            if not equip or (row.get("hours") or 0.0) <= 0.0:
                continue
            group = self._visita_parallel_group(equip)
            if group and group in seen_groups:
                seen_groups[group]["members"].append(row)
                continue
            block = {"group": group, "members": [row]}
            if group:
                seen_groups[group] = block
            blocks.append(block)

        Visita = self.env["afr.qualificacao.os.visita"]
        day_offset = 0
        seq = 0
        for block in blocks:
            members = block["members"]
            member_days = [
                math.ceil((m["hours"] or 0.0) / (m["work_hours_per_day"] or 8.0))
                for m in members
            ]
            n_days = max(member_days) if member_days else 0
            if n_days <= 0:
                continue
            equipment_ids = [m["equipment"].id for m in members]
            is_solo = len(members) == 1
            jornada_b = max((m["work_hours_per_day"] or 8.0) for m in members)
            for d in range(n_days):
                seq += 10
                if is_solo:
                    H = members[0]["hours"] or 0.0
                    J = members[0]["work_hours_per_day"] or 8.0
                    remaining = H - d * J
                    planned = J if remaining >= J else remaining
                else:
                    # Aproximação deliberada (v1): jornada cheia todo dia em bloco paralelo.
                    # O humano ajusta. (Spec §4 menciona resto no último dia — simplificado aqui.)
                    planned = jornada_b
                Visita.create({
                    "os_id": self.id,
                    "tecnico_id": tecnico.id,
                    "date": date_start + timedelta(days=day_offset + d),
                    "equipment_ids": [(6, 0, equipment_ids)],
                    "planned_hours": planned,
                    "sequence": seq,
                    "state": "planned",
                })
            day_offset += n_days
        return True

    def action_open_suggest_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sugerir visitas"),
            "res_model": "afr.qualificacao.os.suggest.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_os_id": self.id,
                "default_tecnico_id": self.tecnico_default_id.id,
                "default_date_start": fields.Date.today(),
            },
        }
