# -*- coding: utf-8 -*-
"""
Estende hr.employee com campos para definir o escopo de equipamentos
que o funcionário pode solicitar no portal (Solicitação de Serviço).

- request_service_scope: "Apenas Departamento", "Todos" ou "Seleção"
- request_service_equipment_ids: quando "Seleção", lista de equipamentos permitidos
"""

from odoo import api, fields, models


class HrEmployeeEquipmentSelection(models.Model):
    """
    Linha de equipamento permitido para solicitação de serviço por funcionário.
    Usado quando request_service_scope = 'selection' no hr.employee.
    """
    _name = "hr.employee.equipment.selection"
    _description = "Equipamento para Solicitação (Funcionário)"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Funcionário",
        required=True,
        ondelete="cascade",
        index=True,
    )
    equipment_id = fields.Many2one(
        "engc.equipment",
        string="Equipamento",
        required=True,
        ondelete="cascade",
        check_company=True,
    )
    company_id = fields.Many2one(
        related="employee_id.company_id",
        store=True,
        readonly=True,
    )

    _sql_constraints = [
        (
            "employee_equipment_uniq",
            "UNIQUE(employee_id, equipment_id)",
            "O equipamento já está na lista deste funcionário.",
        ),
    ]


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    # Escopo de equipamentos que o funcionário pode solicitar no portal
    REQUEST_SERVICE_SCOPE = [
        ("department", "Apenas Departamento"),
        ("all", "Todos"),
        ("selection", "Seleção"),
    ]

    request_service_scope = fields.Selection(
        REQUEST_SERVICE_SCOPE,
        string="Solicitar Serviço",
        default="department",
        help="Define quais equipamentos este funcionário pode selecionar ao criar uma Solicitação de Serviço no portal: "
             "Apenas Departamento (do seu departamento), Todos (da empresa) ou Seleção (lista abaixo).",
    )
    request_service_equipment_ids = fields.One2many(
        "hr.employee.equipment.selection",
        "employee_id",
        string="Equipamentos para Solicitação",
        help="Quando 'Solicitar Serviço' = Seleção, apenas estes equipamentos aparecem no portal.",
    )
