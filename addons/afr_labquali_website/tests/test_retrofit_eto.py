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

    # ---- Task 6: painel explodido, faixa de fases, injeção por peso ----

    def _html(self):
        r = self.url_open("/retrofit/eto")
        self.assertEqual(r.status_code, 200)
        return r.text

    def test_panel_scene(self):
        html = self._html()
        for s in (
            'seqp/p_{iiii}.webp:70:1"',
            "CLP Delta DVP-SE",
            "IHM Delta DOP-107",
            "Modbus TCP",
            "balança",
            # what stays and what is replaced
            "Fica",
            "vaso, portas, bombas e camisa",
            "Troca",
            "automação e instrumentação",
            "PT100, transdutor de pressão, umidade e balança do cilindro",
        ):
            self.assertIn(s, html)

    def test_phase_strip(self):
        html = self._html()
        start = html.index('id="fases"')
        end = html.index("</ol>", start)          # the strip itself, not later sections that name phases
        html = html[:end]
        pos = start
        for name in (
            "Aquecimento", "Leak test", "Acondicionamento", "Umidificação", "Injeção de ETO",
            "Exposição", "Lavagens N2", "Aeração", "Hiperventilação",
        ):
            nxt = html.find(name, pos)
            self.assertGreater(nxt, pos - 1, "%s missing or out of order in #fases" % name)
            pos = nxt + len(name)

    def test_injection_data(self):
        import json
        import re
        html = self._html()
        m = re.search(r'<script type="application/json" id="eto-data">(.*?)</script>', html, re.S)
        self.assertTrue(m, "eto-data block missing")
        d = json.loads(m.group(1))
        self.assertEqual(d["steps"], 5)
        self.assertEqual(round(d["steps"] * d["step_kg"], 2), d["total_kg"])
        self.assertEqual(d["total_kg"], 0.90)
        self.assertEqual(round(d["cyl_start"] - d["cyl_end"], 2), d["total_kg"])
        self.assertTrue(d["p_min"] <= d["p_start"] < d["p_end"] <= d["p_max"])
        for s in (
            "ETO dosado por peso, não por estimativa",
            "O relatório registra a massa exata injetada.",
            "window.LQ_ETO",
            'seqe/e_{iiii}.webp:60:1"',
        ):
            self.assertIn(s, html)

        # the static screen-reader summary must agree with the data block
        def br(v, n):
            return ("−" if v < 0 else "") + ("%.*f" % (n, abs(v))).replace(".", ",")
        sm = re.search(r'<p class="sr-only" id="eto-sum">(.*?)</p>', html, re.S)
        self.assertTrue(sm, "static injection summary missing")
        for s in (br(d["total_kg"], 2), br(d["cyl_start"], 2), br(d["cyl_end"], 2),
                  br(d["p_start"], 3), br(d["p_end"], 3)):
            self.assertIn(s, sm.group(1))

    def test_injection_frame(self):
        for url in ("/retrofit/eto/seqe/e_0060.webp", "/retrofit/eto/seqp/p_0070.webp"):
            r = self.url_open(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertEqual(r.headers.get("Content-Type"), "image/webp", url)
