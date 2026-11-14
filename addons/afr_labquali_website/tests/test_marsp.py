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
