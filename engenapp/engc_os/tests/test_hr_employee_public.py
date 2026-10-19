from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHrEmployeePublicMirror(TransactionCase):
    """Usuário sem grupo HR lê hr.employee via hr.employee.public; os campos de
    escopo de Solicitação de Serviço precisam existir lá (senão AccessError)."""

    def setUp(self):
        super().setUp()
        self.user = self.env["res.users"].create({
            "name": "Sem HR",
            "login": "engc_os_no_hr_user",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        self.employee = self.env["hr.employee"].create({
            "name": "Funcionario Escopo",
            "request_service_scope": "all",
        })

    def test_non_hr_user_reads_request_service_scope(self):
        self.assertFalse(self.user.has_group("hr.group_hr_user"))
        emp = self.employee.with_user(self.user)
        self.assertEqual(emp.request_service_scope, "all")
        self.assertFalse(emp.request_service_equipment_ids)
        vals = emp.read(["request_service_scope", "request_service_equipment_ids"])
        self.assertEqual(vals[0]["request_service_scope"], "all")
        pub = self.env["hr.employee.public"].with_user(self.user).browse(self.employee.id)
        self.assertEqual(pub.request_service_scope, "all")
