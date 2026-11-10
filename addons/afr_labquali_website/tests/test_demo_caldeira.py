import json
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
