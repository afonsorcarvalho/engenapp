from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestDemoCaldeira(HttpCase):
    """The NR-13 boiler demo is served by controllers/demos.py like its siblings."""

    def test_page(self):
        r = self.url_open("/qualificacao/caldeira")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Inspeção de segurança NR-13", r.text)
        self.assertIn("Categoria B", r.text)
        for sid in ("inicio", "placa", "etapas", "ultrassom", "valvula", "relatorio"):
            self.assertIn('id="%s"' % sid, r.text)

    def test_hero_frame(self):
        r = self.url_open("/qualificacao/caldeira/seq/f_0001.webp")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get("Content-Type"), "image/webp")

    def test_traversal_rejected(self):
        # A literal "/../" is collapsed by requests before sending (the request
        # would hit /qualificacao/autoclave/index.html). Percent-encoded dots
        # survive that step and go out on the wire as "/caldeira/../".
        r = self.url_open("/qualificacao/caldeira/%2e%2e/autoclave/index.html")
        self.assertIn("/caldeira/../", r.request.url)
        self.assertEqual(r.status_code, 404)
