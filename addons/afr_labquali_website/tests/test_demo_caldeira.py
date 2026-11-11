import json
import os
import re

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestDemoCaldeira(HttpCase):
    """The NR-13 boiler demo is served by controllers/demos.py like its siblings."""

    def test_page(self):
        r = self.url_open("/qualificacao/caldeira")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Inspeção de segurança NR-13", r.text)
        self.assertIn("Categoria B", r.text)
        for sid in ("inicio", "placa", "etapas", "ultrassom", "valvula", "relatorio", "contato"):
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

    def test_ultrasound_points(self):
        r = self.url_open("/qualificacao/caldeira")
        m = re.search(
            r'<script type="application/json" id="ut-data">(.*?)</script>', r.text, re.S
        )
        self.assertTrue(m, "ut-data JSON block missing")
        pts = json.loads(m.group(1))["points"]
        self.assertEqual(len(pts), 12)
        self.assertEqual(
            [p["id"] for p in pts],
            ["C1", "C2", "C3", "C4", "C5", "C6", "E1", "E2", "E3", "F1", "F2", "F3"],
        )
        self.assertEqual(
            [p["read"] for p in pts],
            [12.4, 12.5, 12.2, 12.6, 12.3, 12.1, 18.6, 18.4, 17.9, 12.0, 11.4, 10.8],
        )
        for p in pts:
            self.assertGreater(p["read"], p["min"], p["id"])
            self.assertTrue(0 <= p["x"] <= 100 and 0 <= p["y"] <= 100, p["id"])
        warn = [p["id"] for p in pts if p["read"] - p["min"] < 1.5]
        self.assertEqual(warn, ["F3"])
        self.assertIn("window.LQ_UT", r.text)
        self.assertIn("0,16 mm/ano", r.text)
        self.assertIn("13.4.4.6", r.text)

    def test_valve_frame(self):
        r = self.url_open("/qualificacao/caldeira/seqv/v_0038.webp")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get("Content-Type"), "image/webp")

    def test_safety_valve(self):
        r = self.url_open("/qualificacao/caldeira")
        self.assertIn('data-sc-sequence="', r.text)
        self.assertIn('seqv/v_{iiii}.webp:80:1"', r.text)
        # data-sc-clip-map="travel" only changes the clip progress (a.vp) used by video
        # scrubs; canvas sequences are drawn by drawSeq() from the act's p, which is
        # already the pinned travel. So this assertion documents intent, nothing more.
        self.assertIn('data-sc-clip-map="travel"', r.text)
        m = re.search(
            r'<script type="application/json" id="psv-data">(.*?)</script>', r.text, re.S
        )
        self.assertTrue(m, "psv-data JSON block missing")
        d = json.loads(m.group(1))
        self.assertEqual(d["pops"], [38, 54, 70])
        self.assertEqual(d["pressures"], [10.42, 10.47, 10.45])
        self.assertEqual(d["pmta"], 10.5)
        self.assertEqual(d["cert"], "CV-2026-0187")
        for p in d["pressures"]:
            self.assertLessEqual(p, d["pmta"])
            self.assertGreaterEqual(p, d["pmta"] * 0.97)
        self.assertIn("window.LQ_PSV", r.text)
        self.assertIn('id="psv-kgf"', r.text)
        self.assertIn("13.4.4.7.1", r.text)
        self.assertIn("13.4.1.2 'a'", r.text)

    def test_ultrasound_coverage(self):
        # nominal / minimum per region, the furnace timeline and the PLH recommendation
        r = self.url_open("/qualificacao/caldeira")
        m = re.search(
            r'<script type="application/json" id="ut-data">(.*?)</script>', r.text, re.S
        )
        pts = json.loads(m.group(1))["points"]
        expect = {"C": (12.7, 10.0), "E": (19.0, 15.0), "F": (12.7, 9.5)}
        for p in pts:
            self.assertEqual((p["nominal"], p["min"]), expect[p["id"][0]], p["id"])
        for year in ("2014", "2026", "2034", "2039"):
            self.assertIn("<b>%s</b>" % year, r.text)
        self.assertIn("(13.4.4.6)", r.text)
        self.assertIn("Reinspecionar fornalha em 12 meses", r.text)
        self.assertIn("metade da vida remanescente", r.text)

    def test_internal_stills(self):
        for n in (1, 2):
            r = self.url_open("/qualificacao/caldeira/still/interno_%d.webp" % n)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.headers.get("Content-Type"), "image/webp")

    def test_report_and_cta(self):
        r = self.url_open("/qualificacao/caldeira")
        html = r.text
        self.assertIn('id="relatorio" data-sc-act="pan"', html)
        self.assertIn("data-sc-pan=", html)
        self.assertGreaterEqual(html.count('href="#contato"'), 2)
        self.assertNotIn('class="btn" href="#relatorio"', html)
        self.assertIn('id="quote"', html)
        self.assertIn('href="/qualificacao/autoclave"', html)
        self.assertIn("Também inspecionamos autoclaves e vasos de pressão", html)
        self.assertIn("Conteúdo mínimo conforme 13.4.4.12", html)
        self.assertIn("CREA-MA 000000-0 · ART nº 0000000", html)
        self.assertIn("11/2027", html)
        self.assertIn("still/interno_1.webp", html)
        self.assertIn("still/interno_2.webp", html)
        # the report tables are generated from the page data, not hand-copied
        self.assertIn("LQ_UT.points", html)
        self.assertIn("LQ_PSV.cert", html)

    def test_copy_rigor(self):
        html = self.url_open("/qualificacao/caldeira").text
        self.assertIsNone(re.search(r"\bPH\b", html, re.I), "use PLH, never PH")
        low = html.lower()
        for bad in ("teste hidrostático periódico", "aposentad", "categoria por pmta"):
            self.assertNotIn(bad, low)
        for good in ("PLH", "Profissional Legalmente Habilitado", "13.4.4.12"):
            self.assertIn(good, html)
        # one illustrative-data disclaimer for the whole page
        self.assertEqual(html.count("Dados ilustrativos de uma caldeira fictícia"), 1)

    def test_accessibility(self):
        html = self.url_open("/qualificacao/caldeira").text
        # numbers rewritten every frame must not sit in a live region
        self.assertNotRegex(html, r'aria-live="[^"]+"[^>]*>\s*<b id="psv-kgf"')
        self.assertNotIn('class="psv-read" aria-live', html)
        self.assertNotIn('id="ut-dev" aria-live', html)
        self.assertIn('id="ut-live"', html)
        self.assertIn('id="psv-stamp" aria-hidden="true"', html)
        self.assertIn('id="ut-card" aria-hidden="true"', html)

    def test_size_budget(self):
        root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "demos", "caldeira")
        total = 0
        for d, _dirs, files in os.walk(root):
            total += sum(os.path.getsize(os.path.join(d, f)) for f in files)
        self.assertGreater(total, 0)
        self.assertLessEqual(total, 12 * 1024 * 1024, "caldeira demo is %.2f MB" % (total / 1048576.0))
