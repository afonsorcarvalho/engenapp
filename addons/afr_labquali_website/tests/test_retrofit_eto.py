from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestRetrofitEto(HttpCase):
    """The ETO retrofit landing page is served at /retrofit/eto by controllers/demos.py."""

    def test_page(self):
        r = self.url_open("/retrofit/eto")
        self.assertEqual(r.status_code, 200)
        self.assertIn(
            "Retrofit de automação ETO: vida nova ao equipamento, conformidade ao processo", r.text
        )
        self.assertIn(
            "CLP e IHM novos, ciclo totalmente rastreável e validação do software pela Labquali.", r.text
        )
        self.assertIn("Quando o CLP para, a produção para", r.text)
        for sid in ("inicio", "dor", "painel", "fases", "injecao", "seguranca", "registro", "contato"):
            self.assertIn('id="%s"' % sid, r.text)

    def test_hero_frame(self):
        r = self.url_open("/retrofit/eto/seq/f_0001.webp")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get("Content-Type"), "image/webp")

    def test_traversal_rejected(self):
        # Percent-encoded dots survive requests' path normalisation and reach the server.
        r = self.url_open("/retrofit/eto/%2e%2e/caldeira/index.html")
        self.assertIn("/eto/../", r.request.url)
        self.assertEqual(r.status_code, 404)

    def test_wrong_prefix_404(self):
        for url in ("/retrofit/caldeira", "/qualificacao/eto", "/inspecao/eto"):
            self.assertEqual(self.url_open(url).status_code, 404, url)

    def test_siblings_unchanged(self):
        self.assertEqual(self.url_open("/inspecao/caldeira").status_code, 200)
        self.assertEqual(self.url_open("/qualificacao/autoclave").status_code, 200)
