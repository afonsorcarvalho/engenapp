import base64
import uuid

from odoo.tests.common import Form, TransactionCase, tagged


@tagged("post_install", "-at_install", "afr_ecm_account")
class TestBridgeAccountEcm(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AccountMove = cls.env["account.move"]
        cls.File = cls.env["dms.file"]
        cls.Directory = cls.env["dms.directory"]

        cls.access_group = cls.env["dms.access.group"].create(
            {
                "name": "Bridge Test ACL",
                "perm_create": True,
                "perm_write": True,
                "perm_unlink": True,
                "group_ids": [(4, cls.env.ref("afr_ecm.group_ecm_user").id)],
            }
        )
        cls.storage = cls.env["dms.storage"].create(
            {"name": "Bridge Storage", "save_type": "database"}
        )
        # account.move minimal — garante journal sale
        cls.partner = cls.env["res.partner"].create({"name": "Cliente Bridge"})
        company = cls.env.company
        journal = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", company.id)], limit=1
        )
        if not journal:
            journal = cls.env["account.journal"].create(
                {
                    "name": "Test Sales",
                    "code": "TSAL",
                    "type": "sale",
                    "company_id": company.id,
                }
            )
        cls.move = cls.AccountMove.create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "journal_id": journal.id,
            }
        )
        # diretório vinculado ao account.move
        dir_form = Form(cls.Directory)
        dir_form.name = "Faturas " + uuid.uuid4().hex[:6]
        dir_form.is_root_directory = True
        dir_form.storage_id = cls.storage
        dir_form.group_ids.add(cls.access_group)
        cls.dir_root = dir_form.save()
        cls.dir_root.write(
            {
                "res_model": "account.move",
                "res_id": cls.move.id,
            }
        )

    @classmethod
    def _content(cls):
        return base64.b64encode(b"\xff content")

    def test_compute_account_move_id(self):
        f = self.File.create(
            {
                "name": "fatura.pdf",
                "directory_id": self.dir_root.id,
                "content": self._content(),
            }
        )
        self.assertEqual(f.account_move_id, self.move)

    def test_auto_classify_invoice_type(self):
        invoice_type = self.env.ref("afr_ecm.doc_type_invoice")
        f = self.File.create(
            {
                "name": "fatura2.pdf",
                "directory_id": self.dir_root.id,
                "content": self._content(),
            }
        )
        self.assertEqual(f.document_type_id, invoice_type)

    def test_no_classify_when_directory_unrelated(self):
        # diretório sem res_model
        other = self.Directory.create(
            {
                "name": "Outro",
                "is_root_directory": True,
                "storage_id": self.storage.id,
                "group_ids": [(4, self.access_group.id)],
            }
        )
        f = self.File.create(
            {
                "name": "outro.pdf",
                "directory_id": other.id,
                "content": self._content(),
            }
        )
        self.assertFalse(f.account_move_id)
        self.assertFalse(f.document_type_id)

    def test_account_move_smart_button_count(self):
        self.File.create(
            {
                "name": "f1.pdf",
                "directory_id": self.dir_root.id,
                "content": self._content(),
            }
        )
        self.File.create(
            {
                "name": "f2.pdf",
                "directory_id": self.dir_root.id,
                "content": self._content(),
            }
        )
        self.move.invalidate_recordset(["ecm_file_count"])
        self.assertEqual(self.move.ecm_file_count, 2)
