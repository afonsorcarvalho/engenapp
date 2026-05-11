from odoo import api, fields, models


class DmsFile(models.Model):
    _inherit = "dms.file"

    account_move_id = fields.Many2one(
        "account.move",
        string="Documento Contábil",
        compute="_compute_account_move_id",
        store=True,
        index=True,
        help="Calculado a partir do diretório vinculado a um account.move (account_dms_field).",
    )

    @api.depends("directory_id", "directory_id.parent_id", "directory_id.res_model", "directory_id.res_id")
    def _compute_account_move_id(self):
        for rec in self:
            move = self.env["account.move"]
            d = rec.directory_id
            # sobe hierarquia até achar diretório vinculado a account.move
            visited = set()
            while d and d.id not in visited:
                visited.add(d.id)
                if d.res_model == "account.move" and d.res_id:
                    move = self.env["account.move"].browse(d.res_id).exists()
                    break
                d = d.parent_id
            rec.account_move_id = move

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        invoice_type = self.env.ref(
            "afr_ecm.doc_type_invoice", raise_if_not_found=False
        )
        if invoice_type:
            for rec in records:
                if rec.account_move_id and not rec.document_type_id:
                    rec.document_type_id = invoice_type
                    # dispara onchange manualmente pra defaults (confidentiality)
                    if invoice_type.default_confidentiality and (
                        not rec.confidentiality or rec.confidentiality == "internal"
                    ):
                        rec.confidentiality = invoice_type.default_confidentiality
        return records
