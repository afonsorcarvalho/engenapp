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

    # ---- Task 7: segurança, registro, contato, rigor do copy, orçamento ----

    FORBIDDEN = ("part 11", "criptograf", "assinatura eletrônica", "supervisório", "detector de eto",
                 "marsp", "montroiz")
    FORBIDDEN_WORDS = ("hash", "ntp", "nuvem")

    def _section(self, html, sid):
        start = html.index('id="%s"' % sid)
        end = html.find("<section", start + 1)
        return html[start:end if end > 0 else len(html)]

    def test_safety_scene(self):
        sec = self._section(self._html(), "seguranca")
        for s in (
            "Alarme que diz o que fazer",
            "ISA-18.2",
            "próxima ação",
            "próxima ação: trocar o cilindro e confirmar na IHM",
            "TROCAR CILINDRO DE ETO",
            "pressão atmosférica",
            "lavagens N2",
            "rotina de segurança",
        ):
            self.assertIn(s, sec)

    def test_record_scene(self):
        import json
        import re
        html = self._html()
        sec = self._section(html, "registro")
        for s in (
            "Cada ciclo deixa um registro completo",
            "Quem instala é quem valida",
            "QI", "QO", "QD",
            "validação do software",
            "APROVADO",
            "CSV",
        ):
            self.assertIn(s, sec)
        # the report reads the injected mass from the injection data, and its static fallback agrees
        self.assertIn("LQ_ETO.total_kg", html)
        d = json.loads(re.search(r'id="eto-data">(.*?)</script>', html, re.S).group(1))
        m = re.search(r'id="rep-mass">([^<]*)<', sec)
        self.assertTrue(m, "report mass field missing")
        self.assertEqual(m.group(1).strip(), ("%.2f" % d["total_kg"]).replace(".", ",") + " kg")
        # blank signature lines for the operator and the person in charge
        for who in ("Operador", "Responsável"):
            self.assertRegex(sec, r'<div class="sig">\s*<i></i>\s*<span>%s</span>' % who)

    def test_cta(self):
        html = self._html()
        sec = self._section(html, "contato")
        for s in ('id="quote"', "Agende uma avaliação técnica", "mailto:labquali@labquali.com.br", "Retrofit ETO · "):
            self.assertIn(s, html)
        self.assertIn('id="quote"', sec)
        self.assertGreaterEqual(html.count('href="#contato"'), 2)

    def test_copy_rigor(self):
        import re
        html = self._html()
        text = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", html, flags=re.S | re.I)
        low = text.lower()
        for bad in self.FORBIDDEN:
            self.assertNotIn(bad, low)
        for bad in self.FORBIDDEN_WORDS:
            self.assertIsNone(re.search(r"\b%s\b" % bad, low), bad)
        self.assertNotIn("11135", low)
        self.assertNotIn("rdc", low)
        self.assertIn("óxido de etileno (ETO)", text)
        self.assertIn("Dados ilustrativos de um ciclo de demonstração", text)

    def test_size_budget(self):
        import os
        root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "demos", "eto")
        total = 0
        for d, _dirs, files in os.walk(root):
            total += sum(os.path.getsize(os.path.join(d, f)) for f in files)
        self.assertGreater(total, 0)
        self.assertLessEqual(total, 12 * 1024 * 1024, "eto demo is %.2f MB" % (total / 1048576.0))
