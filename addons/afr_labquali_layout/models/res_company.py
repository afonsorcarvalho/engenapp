from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    lq_confidential_default = fields.Boolean(
        string="Confidential Stamp on Reports",
        default=False,
        help=(
            "When enabled, all LabQuali-layout reports print a "
            "CONFIDENCIAL stamp in the top-right corner. Can also "
            "be triggered per-report via context key 'lq_confidential': True."
        ),
    )
