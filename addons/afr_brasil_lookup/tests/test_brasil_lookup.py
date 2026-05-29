from unittest.mock import patch
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


FAKE_CEP_RESPONSE = {
    "cep": "01310100",
    "state": "SP",
    "city": "São Paulo",
    "neighborhood": "Bela Vista",
    "street": "Avenida Paulista",
    "service": "open-cep",
    "location": {"type": "Point", "coordinates": {"longitude": "-46.6555", "latitude": "-23.5614"}},
}

FAKE_CNPJ_RESPONSE = {
    "taxId": "11222333000181",
    "company": {
        "name": "ACME INDUSTRIA LTDA",
        "equity": 100000,
    },
    "alias": "ACME",
    "founded": "2000-01-15",
    "statusDate": "2000-01-15",
    "status": {"id": 2, "text": "Ativa"},
    "address": {
        "street": "Rua das Flores",
        "number": "123",
        "details": "Sala 4",
        "district": "Centro",
        "city": "São Paulo",
        "state": "SP",
        "zip": "01001000",
        "country": {"id": 76, "name": "Brasil"},
    },
    "phones": [{"area": "11", "number": "33334444"}],
    "emails": [{"address": "contato@acme.com.br"}],
    "registrations": [
        {"number": "111222333", "state": "SP", "enabled": True, "statusDate": "2020-01-01"}
    ],
}


class TestBrasilLookup(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})
        cls.br = cls.env.ref("base.br")
        cls.state_sp = cls.env["res.country.state"].search(
            [("country_id", "=", cls.br.id), ("code", "=", "SP")], limit=1
        )

    # ---------------- CEP ----------------

    def test_cep_strip_non_digits(self):
        self.assertEqual(self.partner._brl_clean_digits("01310-100"), "01310100")
        self.assertEqual(self.partner._brl_clean_digits(" 01.310-100 "), "01310100")

    def test_cep_invalid_length_raises(self):
        with self.assertRaises(UserError):
            self.partner.with_context(zip="123").action_brl_lookup_cep()

    @patch("odoo.addons.afr_brasil_lookup.models.res_partner._http_get_json")
    def test_cep_populates_address(self, mock_http):
        mock_http.return_value = FAKE_CEP_RESPONSE
        self.partner.zip = "01310-100"
        self.partner.action_brl_lookup_cep()
        self.assertEqual(self.partner.street, "Avenida Paulista")
        self.assertEqual(self.partner.city, "São Paulo")
        self.assertEqual(self.partner.state_id, self.state_sp)
        self.assertEqual(self.partner.country_id, self.br)
        self.assertEqual(self.partner.zip, "01310-100")

    @patch("odoo.addons.afr_brasil_lookup.models.res_partner._http_get_json")
    def test_cep_not_found_raises(self, mock_http):
        mock_http.side_effect = UserError("CEP não encontrado.")
        self.partner.zip = "00000-000"
        with self.assertRaises(UserError):
            self.partner.action_brl_lookup_cep()

    # ---------------- CNPJ ----------------

    def test_cnpj_invalid_check_digit_raises(self):
        self.partner.vat = "11.222.333/0001-00"
        with self.assertRaises(UserError):
            self.partner.action_brl_lookup_cnpj()

    @patch("odoo.addons.afr_brasil_lookup.models.res_partner._http_get_json")
    def test_cnpj_populates_company(self, mock_http):
        mock_http.return_value = FAKE_CNPJ_RESPONSE
        self.partner.vat = "11.222.333/0001-81"
        self.partner.action_brl_lookup_cnpj()
        self.assertEqual(self.partner.name, "ACME INDUSTRIA LTDA")
        self.assertEqual(self.partner.street, "Rua das Flores, 123")
        self.assertEqual(self.partner.street2, "Sala 4 - Centro")
        self.assertEqual(self.partner.city, "São Paulo")
        self.assertEqual(self.partner.state_id, self.state_sp)
        self.assertEqual(self.partner.country_id, self.br)
        self.assertEqual(self.partner.zip, "01001-000")
        self.assertEqual(self.partner.phone, "+55 11 3333-4444")
        self.assertEqual(self.partner.email, "contato@acme.com.br")
        self.assertTrue(self.partner.is_company)

    @patch("odoo.addons.afr_brasil_lookup.models.res_partner._http_get_json")
    def test_cnpj_rate_limit_raises(self, mock_http):
        mock_http.side_effect = UserError("Limite de consultas atingido. Tente novamente em alguns minutos.")
        self.partner.vat = "11.222.333/0001-81"
        with self.assertRaises(UserError):
            self.partner.action_brl_lookup_cnpj()

    # ---------------- Onchange ----------------

    def test_onchange_cep_disabled_by_default(self):
        # Por padrão ICP auto_fill_cep = False → onchange não chama HTTP
        with patch("odoo.addons.afr_brasil_lookup.models.res_partner._http_get_json") as m:
            self.partner.zip = "01310-100"
            self.partner._onchange_zip_brl()
            m.assert_not_called()

    @patch("odoo.addons.afr_brasil_lookup.models.res_partner._http_get_json")
    def test_onchange_cep_enabled_by_icp(self, mock_http):
        mock_http.return_value = FAKE_CEP_RESPONSE
        self.env["ir.config_parameter"].sudo().set_param(
            "afr_brasil_lookup.auto_fill_cep", "True"
        )
        self.partner.zip = "01310-100"
        self.partner._onchange_zip_brl()
        self.assertEqual(self.partner.street, "Avenida Paulista")
