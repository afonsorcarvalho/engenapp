from odoo import _, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    ecm_file_count = fields.Integer(
        string="Documentos ECM",
        compute="_compute_ecm_file_count",
    )

    def _compute_ecm_file_count(self):
        File = self.env["dms.file"]
        for rec in self:
            rec.ecm_file_count = File.search_count(
                [("account_move_id", "=", rec.id)]
            )

    def action_view_ecm_files(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Documentos ECM"),
            "res_model": "dms.file",
            "view_mode": "tree,form",
            "domain": [("account_move_id", "=", self.id)],
            "context": {"default_account_move_id": self.id},
        }
