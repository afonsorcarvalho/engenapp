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


class BaseDocumentLayout(models.TransientModel):
    """Expose lq_confidential_default on the Configure Document Layout wizard.

    The QWeb template binds `company` to the wizard record during preview render,
    so the custom field must exist on this transient too — otherwise preview
    crashes with AttributeError.
    """
    _inherit = "base.document.layout"

    lq_confidential_default = fields.Boolean(
        related="company_id.lq_confidential_default",
        readonly=False,
    )
