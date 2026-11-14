import os
import re

from odoo.modules.module import get_module_resource
from odoo.tests import HttpCase, TransactionCase, tagged

FILES = ("logo-symbol.svg", "logo-light.svg", "logo-dark.svg", "logo-mono.svg", "favicon.svg", "marsp.css")
SVGS = tuple(f for f in FILES if f.endswith(".svg"))
PALETTE = (
    "#071E32", "#0A3D62", "#1E6091", "#FF6B35", "#C2410C",
    "#5A7184", "#C6CDD4", "#E0E8F0", "#EEF2F5", "#F4F7FA",
)


@tagged("post_install", "-at_install")
class TestMarspBrand(TransactionCase):
    """Brand files shared by every MARSP page live in static/demos/_marsp/."""

    def _read(self, name):
        path = get_module_resource("afr_labquali_website", "static", "demos", "_marsp", name)
        self.assertTrue(path, "%s missing" % name)
        with open(path, encoding="utf-8") as fh:
            return fh.read()

    def test_files_exist(self):
        for name in FILES:
            self.assertTrue(self._read(name), name)

    def test_svgs_are_flat(self):
        for name in SVGS:
            svg = self._read(name)
            for bad in ("<mask", "<clipPath", "<image", "<script", "font-family"):
                self.assertNotIn(bad, svg, "%s contains %s" % (name, bad))

    def test_light_versions(self):
        for name in ("logo-symbol.svg", "logo-light.svg"):
            svg = self._read(name)
            self.assertIn("#0A3D62", svg, name)
            self.assertIn("#FF6B35", svg, name)

    def test_dark_version(self):
        svg = self._read("logo-dark.svg").upper()
        self.assertTrue("#FFFFFF" in svg or "#FFF\"" in svg, "no white")
        self.assertIn("#FF6B35", svg)
        self.assertNotIn("#0A3D62", svg)

    def test_mono_uses_current_color_only(self):
        svg = self._read("logo-mono.svg")
        self.assertIn("currentColor", svg)
        self.assertFalse(re.search(r"#[0-9A-Fa-f]{3,6}\b", svg), "hex colour in mono logo")
        for fill in re.findall(r'(?:fill|stroke)="([^"]*)"', svg):
            self.assertIn(fill, ("currentColor", "none"))

    def test_css_tokens(self):
        css = self._read("marsp.css").upper()
        for hex_ in PALETTE:
            self.assertIn(hex_, css)
        self.assertIn("Michroma", self._read("marsp.css"))
        self.assertIn("Inter", self._read("marsp.css"))


@tagged("post_install", "-at_install")
class TestMarspRoutes(HttpCase):
    """MARSP pages are served at /marsp and /marsp/<slug> by controllers/demos.py."""

    def test_pages(self):
        r = self.url_open("/marsp")
        self.assertEqual(r.status_code, 200)
        self.assertIn("<h1", r.text)
        self.assertEqual(self.url_open("/marsp/autoclave-eto").status_code, 200)

    def test_trailing_slash_redirects(self):
        r = self.url_open("/marsp/", allow_redirects=False)
        self.assertEqual(r.status_code, 301)
        self.assertTrue(r.headers["Location"].endswith("/marsp"))

    def test_unknown_slugs_404(self):
        for slug in ("gerador-de-vapor", "aquecedor-eto", "psicrometro", "eto", "caldeira"):
            self.assertEqual(self.url_open("/marsp/" + slug).status_code, 404, slug)

    def test_wrong_prefix_404(self):
        for url in ("/retrofit/autoclave-eto", "/qualificacao/marsp-vitrine"):
            self.assertEqual(self.url_open(url).status_code, 404, url)

    def test_brand_assets(self):
        r = self.url_open("/marsp/_marsp/logo-symbol.svg")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get("Content-Type"), "image/svg+xml")
        r = self.url_open("/marsp/_marsp/marsp.css")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get("Content-Type"), "text/css")

    def test_traversal_rejected(self):
        r = self.url_open("/marsp/marsp-autoclave-eto/%2e%2e/eto/index.html")
        self.assertIn("/marsp-autoclave-eto/../", r.request.url)
        self.assertEqual(r.status_code, 404)

    def test_asset_folder_whitelist(self):
        for url in ("/marsp/eto/index.html", "/marsp/autoclave/index.html"):
            self.assertEqual(self.url_open(url).status_code, 404, url)

    def test_siblings_unchanged(self):
        for url in ("/retrofit/eto", "/inspecao/caldeira", "/qualificacao/autoclave"):
            self.assertEqual(self.url_open(url).status_code, 200, url)

    def test_shadowed_static_rewrites_brand_path(self):
        from unittest import mock
        from odoo.addons.afr_labquali_website.controllers import demos

        demos._html_cache.clear()
        try:
            with mock.patch.object(demos, "_static_dir_is_ours", return_value=False):
                html = self.url_open("/marsp/autoclave-eto").text
        finally:
            demos._html_cache.clear()
        self.assertNotIn("/afr_labquali_website/static/demos/", html)
        self.assertIn("/marsp/_marsp/marsp.css", html)


@tagged("post_install", "-at_install")
class TestMarspVitrine(HttpCase):
    """/marsp is the line-up: one live model and three "em breve" teasers."""

    SILHOUETTES = ("sil-gerador.svg", "sil-aquecedor.svg", "sil-psicrometro.svg")

    def setUp(self):
        super().setUp()
        r = self.url_open("/marsp")
        self.assertEqual(r.status_code, 200)
        self.html = r.text

    def _section(self, sid):
        m = re.search(r'<section[^>]*\bid="%s".*?</section>' % sid, self.html, re.S)
        self.assertTrue(m, "section #%s missing" % sid)
        return m.group(0)

    def test_sections(self):
        for sid in ("inicio", "linha", "parceria", "proposta"):
            self._section(sid)

    def test_four_products(self):
        for name in ("Autoclave ETO", "Gerador de vapor", "Aquecedor de gás ETO", "Psicrômetro"):
            self.assertIn(name, self.html)
        self.assertIn("MSP 1500-E", self._section("linha"))

    def test_only_autoclave_is_linked(self):
        linha = self._section("linha")
        self.assertEqual(linha.count('href="/marsp/autoclave-eto"'), 1)
        for slug in ("gerador-de-vapor", "aquecedor-eto", "psicrometro"):
            self.assertNotIn("/marsp/" + slug, self.html, slug)

    def test_three_teasers(self):
        self.assertEqual(len(re.findall(r"em breve", self.html, re.I)), 3)

    def test_silhouettes_served(self):
        for name in self.SILHOUETTES:
            self.assertIn(name, self.html, name)
            r = self.url_open("/marsp/marsp-vitrine/" + name)
            self.assertEqual(r.status_code, 200, name)
            self.assertEqual(r.headers.get("Content-Type"), "image/svg+xml", name)

    def test_proposal_mailto(self):
        self.assertIn("mailto:labquali@labquali.com.br?subject=Proposta%20MARSP", self._section("proposta"))

    def test_no_forbidden_content(self):
        for bad in ("amed", "point suture", "medplast", "oximed", "steriliza", "montroiz", "vap-eto"):
            self.assertFalse(re.search(r"\b%s\b" % re.escape(bad), self.html, re.I), bad)
        self.assertNotIn("R$", self.html)


@tagged("post_install", "-at_install")
class TestMarspAutoclave(HttpCase):
    """/marsp/autoclave-eto: the model page (3D opening, highlights, gallery, spec sheet, proposal)."""

    BASE = "/marsp/marsp-autoclave-eto/"
    MAILTO = "mailto:labquali@labquali.com.br?subject=Proposta%20MARSP%20-%20Autoclave%20ETO%20MSP%201500-E"

    def setUp(self):
        super().setUp()
        r = self.url_open("/marsp/autoclave-eto")
        self.assertEqual(r.status_code, 200)
        self.html = r.text
        path = get_module_resource("afr_labquali_website", "static", "demos", "marsp-autoclave-eto", "index.html")
        with open(path, encoding="utf-8") as fh:
            self.source = fh.read()

    def test_names_and_data(self):
        for text in ("MSP 1500-E", "Autoclave ETO", "1000 × 1000 × 1500 mm", "316L"):
            self.assertIn(text, self.html, text)

    def test_sections(self):
        for sid in ("inicio", "destaques", "galeria", "ficha", "linha", "proposta"):
            self.assertRegex(self.html, r'<section[^>]*\bid="%s"' % sid, sid)

    def test_sequences(self):
        # Source keeps the relative template; the controller prefixes it when serving.
        self.assertIn('data-sc-sequence="seq/f_{iiii}.webp', self.source)
        self.assertIn('data-sc-sequence="seqa/a_{iiii}.webp', self.source)
        self.assertRegex(self.html, r'data-sc-sequence="[^"]*/marsp-autoclave-eto/seq/f_\{iiii\}\.webp:150:1"')
        self.assertRegex(self.html, r'data-sc-sequence="[^"]*/marsp-autoclave-eto/seqa/a_\{iiii\}\.webp:70:1"')

    def test_frames_served(self):
        for name in ("seq/f_0001.webp", "seqa/a_0070.webp", "seq-m/f_0150.webp", "seqa-m/a_0001.webp"):
            r = self.url_open(self.BASE + name)
            self.assertEqual(r.status_code, 200, name)
            self.assertEqual(r.headers.get("Content-Type"), "image/webp", name)

    def test_proposal_mailto(self):
        m = re.search(r'<section[^>]*\bid="proposta".*?</section>', self.html, re.S)
        self.assertTrue(m)
        self.assertIn('href="%s"' % self.MAILTO, m.group(0))

    def test_static_fallback(self):
        r = self.url_open(self.BASE + "page.css")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get("Content-Type"), "text/css")
        self.assertIn("prefers-reduced-motion", r.text)
        self.assertRegex(self.html, r'<img[^>]*still-capa\.webp')
        for name in ("scrollcraft.js", "scrollcraft.css"):
            self.assertEqual(self.url_open(self.BASE + name).status_code, 200, name)

    def test_back_to_line(self):
        self.assertGreaterEqual(self.html.count('href="/marsp"'), 2)

    def test_other_models_not_linked(self):
        self.assertNotIn('href="/marsp/gerador-de-vapor"', self.html)
        for slug in ("/marsp/aquecedor-eto", "/marsp/psicrometro"):
            self.assertNotIn(slug, self.html, slug)
        m = re.search(r'<section[^>]*\bid="linha".*?</section>', self.html, re.S)
        self.assertTrue(m)
        self.assertEqual(len(re.findall(r"em breve", m.group(0), re.I)), 3)

    def test_no_forbidden_content(self):
        for bad in ("amed", "point suture", "medplast", "oximed", "steriliza", "montroiz", "vap-eto", "mogi"):
            self.assertFalse(re.search(r"\b%s\b" % re.escape(bad), self.html, re.I), bad)
        self.assertNotIn("R$", self.html)
        self.assertNotIn("CNPJ", self.html)


@tagged("post_install", "-at_install")
class TestMarspGuards(HttpCase):
    """Closing guards: forbidden content and weight budgets for the MARSP folders."""

    FOLDERS = ("marsp-vitrine", "marsp-autoclave-eto", "_marsp")
    BLACKLIST = (
        r"montroiz", r"\bamed\b", r"point suture", r"medplast", r"oximed",
        r"\bsteriliza\b", r"vap-eto", r"R\$",
    )

    def _root(self, folder):
        path = get_module_resource("afr_labquali_website", "static", "demos", folder)
        self.assertTrue(path, folder)
        return path

    def test_no_forbidden_tokens(self):
        scanned = 0
        for folder in self.FOLDERS:
            for dirpath, _dirs, names in os.walk(self._root(folder)):
                for name in names:
                    if not name.endswith((".html", ".css", ".svg")):
                        continue
                    with open(os.path.join(dirpath, name), encoding="utf-8") as fh:
                        text = fh.read()
                    scanned += 1
                    for pat in self.BLACKLIST:
                        self.assertFalse(re.search(pat, text, re.I), "%s in %s/%s" % (pat, folder, name))
        self.assertGreater(scanned, 10)

    def test_weight_budgets(self):
        for folder, limit in (("marsp-autoclave-eto", 12), ("marsp-vitrine", 2)):
            total = sum(
                os.path.getsize(os.path.join(dp, n))
                for dp, _d, names in os.walk(self._root(folder)) for n in names
            )
            self.assertLessEqual(total, limit * 1024 * 1024, "%s is %d bytes" % (folder, total))

    def test_vitrine_image_served(self):
        r = self.url_open("/marsp/marsp-vitrine/autoclave.webp")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get("Content-Type"), "image/webp")

    def test_engine_failure_falls_back_to_static(self):
        path = get_module_resource("afr_labquali_website", "static", "demos", "marsp-autoclave-eto", "index.html")
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        self.assertRegex(src, r"classList\.remove\('m-live'\)")

    def test_brand_css_off_palette_hover_and_reduced_motion(self):
        path = get_module_resource("afr_labquali_website", "static", "demos", "_marsp", "marsp.css")
        with open(path, encoding="utf-8") as fh:
            css = fh.read()
        self.assertNotIn("#ff7f50", css.lower())
        self.assertRegex(css, r"prefers-reduced-motion:\s*reduce")
