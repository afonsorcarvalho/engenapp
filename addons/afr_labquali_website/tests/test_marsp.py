import re

from odoo.modules.module import get_module_resource
from odoo.tests import TransactionCase, tagged

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
