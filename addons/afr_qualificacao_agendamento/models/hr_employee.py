# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    is_tecnico = fields.Boolean(
        string="Técnico de Qualificação",
        help="Marca este empregado como técnico de qualificação. "
             "Aparece no seletor de técnicos do Quadro de Agenda.",
    )
