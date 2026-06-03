# -*- coding: utf-8 -*-
from odoo import fields, models


class AfrQualificacaoOsSuggestWizard(models.TransientModel):
    _name = "afr.qualificacao.os.suggest.wizard"
    _description = "Assistente de sugestão de visitas"

    os_id = fields.Many2one(
        "afr.qualificacao.os", string="OS", required=True, ondelete="cascade"
    )
    tecnico_id = fields.Many2one(
        "hr.employee", string="Técnico", required=True
    )
    date_start = fields.Date(
        string="Data de início", required=True, default=fields.Date.context_today
    )

    def action_generate(self):
        self.ensure_one()
        self.os_id._suggest_visitas(self.tecnico_id, self.date_start)
        return self.os_id.action_view_visitas()
