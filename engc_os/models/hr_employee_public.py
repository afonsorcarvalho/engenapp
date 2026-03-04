# -*- coding: utf-8 -*-
"""
Estende hr.employee.public com os campos de escopo de Solicitação de Serviço.

Quando o usuário não tem permissão total em HR, o Odoo delega leituras de
hr.employee para hr.employee.public. Os campos request_service_scope e
request_service_equipment_ids precisam existir aqui para evitar
ValueError: Invalid field 'request_service_scope' on model 'hr.employee.public'
ao abrir telas que leem funcionário (ex.: executar ordem de serviço).

Usamos campos computados com sudo() em vez de related para evitar recursão
na delegação hr.employee._read -> hr.employee.public.read.
"""

from odoo import api, fields, models


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    request_service_scope = fields.Selection(
        selection=[
            ("department", "Apenas Departamento"),
            ("all", "Todos"),
            ("selection", "Seleção"),
        ],
        string="Solicitar Serviço",
        compute="_compute_request_service_scope",
        compute_sudo=True,
        readonly=True,
    )
    request_service_equipment_ids = fields.One2many(
        "hr.employee.equipment.selection",
        compute="_compute_request_service_equipment_ids",
        compute_sudo=True,
        readonly=True,
    )

    @api.depends("id")
    def _compute_request_service_scope(self):
        """Lê do hr.employee com sudo para não delegar de volta ao public."""
        for rec in self:
            emp = self.env["hr.employee"].sudo().browse(rec.id)
            rec.request_service_scope = emp.request_service_scope if emp.exists() else False

    @api.depends("id")
    def _compute_request_service_equipment_ids(self):
        """Lê do hr.employee com sudo para não delegar de volta ao public."""
        for rec in self:
            emp = self.env["hr.employee"].sudo().browse(rec.id)
            rec.request_service_equipment_ids = emp.request_service_equipment_ids if emp.exists() else self.env["hr.employee.equipment.selection"]
