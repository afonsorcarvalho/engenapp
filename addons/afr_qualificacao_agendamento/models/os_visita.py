# -*- coding: utf-8 -*-
"""Visita de campo de uma OS de Qualificação (afr.qualificacao.os.visita).

Unidade agendável = OS × dia × técnico. Fase A: modelo base, datetimes
computados para a calendar, e detecção de conflito de técnico/deslocamento
(avisos não-bloqueantes — Task 5).
"""
from datetime import datetime, time, timedelta

from pytz import timezone, utc

from odoo import _, api, fields, models
from odoo.exceptions import UserError


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
    os_equipment_ids = fields.Many2many(
        "engc.equipment",
        related="os_id.equipment_ids",
        string="Equipamentos da OS",
        help="Equipamentos elencados na OS (domínio do seletor de equipamentos).",
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

    instrument_ids = fields.Many2many(
        "engc.calibration.instruments",
        "afr_visita_instrument_rel", "visita_id", "instrument_id",
        string="Instrumentos (validador/padrão)",
        help="Instrumentos metrológicos usados nesta visita (atribuição manual).",
    )
    instrument_conflict = fields.Boolean(
        string="Conflito de instrumento", compute="_compute_resource_conflicts"
    )
    instrument_conflict_msg = fields.Char(compute="_compute_resource_conflicts")
    calibration_conflict = fields.Boolean(
        string="Calibração vencida", compute="_compute_resource_conflicts"
    )
    calibration_conflict_msg = fields.Char(compute="_compute_resource_conflicts")

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

    def _instrument_valid_on(self, instrument, day):
        """True se o instrumento tem certificado válido na data `day`."""
        return any(
            c.validate_calibration and c.validate_calibration >= day
            for c in instrument.certificate_ids
        )

    @api.depends("instrument_ids", "date", "date_start", "date_stop")
    def _compute_resource_conflicts(self):
        for r in self:
            r.instrument_conflict = False
            r.instrument_conflict_msg = False
            r.calibration_conflict = False
            r.calibration_conflict_msg = False
            if not r.instrument_ids:
                continue
            # Conflito de recurso: instrumento em OS diferente, janela sobreposta.
            if r.date_start and r.date_stop:
                exclude = [("id", "!=", r._origin.id)] if r._origin.id else []
                clash = self.search(exclude + [
                    ("os_id", "!=", r.os_id.id),
                    ("instrument_ids", "in", r.instrument_ids.ids),
                    ("date_start", "<", r.date_stop),
                    ("date_stop", ">", r.date_start),
                ], limit=1)
                if clash:
                    shared = clash.instrument_ids & r.instrument_ids
                    r.instrument_conflict = True
                    r.instrument_conflict_msg = _(
                        "Instrumento(s) %s já em uso na OS %s no período."
                    ) % (", ".join(shared.mapped("display_name")),
                         clash.os_id.name or _("(sem OS)"))
            # Conflito de calibração: instrumento sem certificado válido na data.
            if r.date:
                expired = r.instrument_ids.filtered(
                    lambda inst: not r._instrument_valid_on(inst, r.date)
                )
                if expired:
                    r.calibration_conflict = True
                    r.calibration_conflict_msg = _(
                        "Calibração vencida/ausente em: %s (data %s)."
                    ) % (", ".join(expired.mapped("display_name")),
                         fields.Date.to_string(r.date))

    @api.onchange("time_start", "planned_hours")
    def _onchange_fill_time_stop(self):
        """Hora fim = hora início + horas previstas (auto)."""
        for r in self:
            if r.planned_hours:
                r.time_stop = r.time_start + r.planned_hours

    @api.onchange("time_stop")
    def _onchange_time_stop_hours(self):
        """Ao alongar a hora fim, aumenta as horas previstas e avisa o usuário.
        Grow-only por desenho: encurtar a hora fim não reduz as horas previstas."""
        self.ensure_one()
        new_hours = self.time_stop - self.time_start
        if new_hours <= 0:
            return
        if new_hours > self.planned_hours:
            old = self.planned_hours
            self.planned_hours = new_hours
            return {"warning": {
                "title": _("Horas previstas atualizadas"),
                "message": _(
                    "A hora fim ampliou as horas previstas de %.2f h "
                    "para %.2f h."
                ) % (old, new_hours),
            }}

    overflow_next_day = fields.Boolean(
        string="Passa do dia",
        compute="_compute_overflow_next_day",
        help="Hora início + horas previstas ultrapassa o fim do dia (24h). "
             "Use 'Dividir em 2 dias' para criar a visita-continuação.",
    )

    @api.depends("time_start", "planned_hours")
    def _compute_overflow_next_day(self):
        for r in self:
            r.overflow_next_day = bool(
                r.planned_hours > 0.0
                and (r.time_start + r.planned_hours) > 24.0
            )

    def _split_overflow(self):
        """Divide a visita: o que cabe até 24h fica no dia; o resto vira uma
        visita-continuação no dia seguinte com o MESMO horário de início
        (mesmo técnico/OS/equip/instrumentos). Retorna a continuação.
        Se a continuação ainda transbordar, ela própria mostra o botão."""
        self.ensure_one()
        fits = 24.0 - self.time_start
        if self.planned_hours <= fits:
            raise UserError(_(
                "Esta visita cabe no dia; não há horas a transbordar."))
        rest = self.planned_hours - fits
        # visita atual fica com o que cabe até o fim do dia
        self.write({"planned_hours": fits, "time_stop": 23.9833})
        # continuação no dia seguinte, MESMO horário de início, com o resto
        cont_stop = self.time_start + rest
        return self.copy({
            "date": self.date + timedelta(days=1),
            "time_start": self.time_start,
            "planned_hours": rest,
            "time_stop": cont_stop if cont_stop <= 24.0 else 23.9833,
            "travel_buffer_hours": 0.0,
        })

    def action_split_overflow(self):
        """Botão do form: divide e abre a visita-continuação."""
        cont = self._split_overflow()
        return {
            "type": "ir.actions.act_window",
            "name": _("Visita-continuação"),
            "res_model": "afr.qualificacao.os.visita",
            "res_id": cont.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def board_split_overflow(self, visita_id):
        """Botão '+' do board: divide a visita (sem abrir form)."""
        self.browse(visita_id)._split_overflow()
        return True

    @api.model
    def board_delete_visita(self, visita_id):
        """Lixeira do board: apaga a visita."""
        self.browse(visita_id).unlink()
        return True

    @api.model
    def board_set_hours(self, visita_id, time_start, time_stop):
        """Edição inline do horário no card do board. Grava início/fim e
        recalcula horas previstas = fim - início (quando válido)."""
        visita = self.browse(visita_id)
        vals = {"time_start": time_start, "time_stop": time_stop}
        if time_stop > time_start:
            vals["planned_hours"] = time_stop - time_start
        visita.write(vals)
        return True

    def action_pull_instruments_from_plan(self):
        """Pré-preenche instrument_ids a partir do plano de recursos (F10) da OS,
        pelas linhas cujos equipamentos batem com os da visita."""
        self.ensure_one()
        lines = self.os_id.resource_plan_line_ids.filtered(
            lambda l: l.instrument_id and (l.equipment_ids & self.equipment_ids)
        )
        self.instrument_ids = [(6, 0, lines.mapped("instrument_id").ids)]
        return True

    @api.model
    def board_fetch(self, date_from, date_to):
        """Dados do board: técnicos com visita no intervalo + visitas serializadas."""
        visitas = self.search([
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ], order="tecnico_id, date, sequence")
        techs = {}
        rows = []
        for v in visitas:
            if v.tecnico_id and v.tecnico_id.id not in techs:
                techs[v.tecnico_id.id] = v.tecnico_id.name
            msgs = [m for m in (
                v.tecnico_conflict_msg, v.travel_conflict_msg,
                v.instrument_conflict_msg, v.calibration_conflict_msg,
            ) if m]
            rows.append({
                "id": v.id,
                "tecnico_id": v.tecnico_id.id or False,
                "date": fields.Date.to_string(v.date),
                "os_id": v.os_id.id or False,
                "os_name": v.os_id.name or "",
                "partner_name": v.partner_id.name or "",
                "planned_hours": round(v.planned_hours, 1),
                "state": v.state,
                "overflow": v.overflow_next_day,
                "time_start": v.time_start,
                "time_stop": v.time_stop,
                "equipment_names": ", ".join(filter(None, v.equipment_ids.mapped(
                    lambda e: e.apelido or e.tag or e.name
                ))),
                "equipment_list": list(filter(None, v.equipment_ids.mapped(
                    lambda e: e.apelido or e.tag or e.name
                ))),
                "instrument_names": ", ".join(
                    filter(None, v.instrument_ids.mapped(
                        lambda i: i.tag or i.id_number or i.name
                    ))
                ),
                "instrument_list": list(filter(None, v.instrument_ids.mapped(
                    lambda i: i.tag or i.id_number or i.name
                ))),
                "conflict": bool(
                    v.tecnico_conflict or v.travel_conflict
                    or v.instrument_conflict or v.calibration_conflict
                ),
                "conflict_msg": " | ".join(msgs),
            })
        technicians = [
            {"id": tid, "name": name}
            for tid, name in sorted(techs.items(), key=lambda x: (x[1] or ""))
        ]
        return {"technicians": technicians, "visitas": rows}

    @api.model
    def board_reschedule(self, visita_id, new_date, new_tecnico_id):
        """Drag-reschedule: grava nova data + técnico. Bloqueia visita realizada."""
        visita = self.browse(visita_id)
        if visita.state == "done":
            raise UserError(_(
                "Não é possível reagendar uma visita já realizada."
            ))
        visita.write({"date": new_date, "tecnico_id": new_tecnico_id})
        return True

    @api.model
    def board_technician_options(self):
        """Técnicos marcados is_tecnico=True, para o seletor do board."""
        techs = self.env["hr.employee"].search([("is_tecnico", "=", True)])
        return [{"id": t.id, "name": t.name} for t in techs]

    @api.model
    def board_os_options(self):
        """OS ativas (não done/cancelled) para o seletor de nova visita."""
        oss = self.env["afr.qualificacao.os"].search([
            ("state", "not in", ("done", "cancelled")),
        ])
        return [{
            "id": o.id,
            "name": "%s - %s" % (o.name or "", o.partner_id.name or ""),
        } for o in oss]

    @api.model
    def board_create_visita(self, os_id, tecnico_id, date):
        """Cria visita mínima (os+técnico+data) a partir do seletor do board."""
        self.create({
            "os_id": os_id,
            "tecnico_id": tecnico_id,
            "date": date,
        })
        return True
