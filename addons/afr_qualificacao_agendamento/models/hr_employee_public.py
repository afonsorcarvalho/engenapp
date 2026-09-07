# -*- coding: utf-8 -*-
"""
Espelha `is_tecnico` em hr.employee.public.

Quando o usuário não tem permissão total em HR — o caso de todo técnico —, o
Odoo delega a leitura de hr.employee para hr.employee.public
(`hr/models/hr_employee.py::_read`). Um campo que exista só no primeiro faz a
delegação estourar:

    ValueError: Invalid field 'is_tecnico' on model 'hr.employee.public'

Na prática isso quebrava o fechamento do relatório do dia no PWA do técnico, que
passa por um `filtered()` sobre o empregado.

Mesmo padrão já usado em `engenapp/engc_os/models/hr_employee_public.py` para
`request_service_scope`: campo computado com sudo em vez de `related`, para não
delegar de volta ao public e entrar em recursão. Sem `@api.depends` porque o
Odoo não aceita depender de `id`; o valor é calculado ao acessar.
"""

from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    is_tecnico = fields.Boolean(
        string="Técnico de Qualificação",
        compute="_compute_is_tecnico",
        compute_sudo=True,
        readonly=True,
    )

    def _compute_is_tecnico(self):
        for rec in self:
            emp = self.env["hr.employee"].sudo().browse(rec.id)
            rec.is_tecnico = emp.is_tecnico if emp.exists() else False
