"""Scroll-driven explainer pages, one per equipment type.

Each page is a self-contained static build under static/demos/<slug>/ (HTML,
scroll engine, 3D render frames). The page is served at /<prefix>/<slug>
and its assets at /<prefix>/<slug>/<file>, where prefix is "qualificacao"
(autoclave, termodesinfectora, estufa, camara-fria), "inspecao" (caldeira) or
"retrofit" (eto).
The MARSP brand has its own prefix: /marsp (vitrine, static/demos/marsp-vitrine/),
/marsp/<slug> (static/demos/marsp-<slug>/) and /marsp/<folder>/<file> for assets.
The legacy /qualificacao/caldeira page redirects (301) to /inspecao/caldeira.

Assets go through this controller instead of /afr_labquali_website/static/:
Odoo 16 maps a module's static dir to the LAST copy of the module found in
addons_path, and the production server keeps an older shadow copy of this
module (inside the monorepo clone) after the real one. Reading through
get_module_resource uses the copy Odoo actually loaded.
"""
import mimetypes
import os
import re

from odoo import http
from odoo.http import request
from odoo.modules.module import get_module_resource

MODULE = "afr_labquali_website"
QUALIFICACAO = ("autoclave", "termodesinfectora", "estufa", "camara-fria")
INSPECAO = ("caldeira",)
RETROFIT = ("eto",)
MARSP = ("autoclave-eto",)
MARSP_FOLDERS = ("marsp-vitrine",) + tuple("marsp-" + s for s in MARSP) + ("_marsp",)
DEMOS = QUALIFICACAO + INSPECAO + RETROFIT
PREFIXES = {"qualificacao": QUALIFICACAO, "inspecao": INSPECAO, "retrofit": RETROFIT, "marsp": MARSP}
_REL_ATTR = re.compile(r'((?:src|href|data-sc-sequence)=")(?![#/]|https?:|mailto:|data:)')
_STATIC_PREFIX = "/%s/static/demos/" % MODULE
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/svg+xml", ".svg")
_html_cache = {}


def _static_dir_is_ours():
    """True when /<module>/static/ is served from the module copy Odoo loaded."""
    ours = get_module_resource(MODULE, "static")
    served = getattr(http.root, "statics", {}).get(MODULE)
    return bool(ours and served and os.path.realpath(ours) == os.path.realpath(served))


def _page_html(folder, prefix):
    key = (prefix, folder)
    if key not in _html_cache:
        path = get_module_resource(MODULE, "static", "demos", folder, "index.html")
        with open(path, encoding="utf-8") as fh:
            html = fh.read()
        if _static_dir_is_ours():
            base = _STATIC_PREFIX                      # plain static route: no DB needed, cached by Odoo
        else:
            base = "/%s/" % prefix                     # shadowed static dir: serve through this controller
            html = html.replace(_STATIC_PREFIX, base)
        rel = base + folder + "/"
        _html_cache[key] = _REL_ATTR.sub(lambda m: m.group(1) + rel, html)
    return _html_cache[key]


def _prefix():
    return request.httprequest.path.split("/")[1]


class LabqualiDemos(http.Controller):

    @http.route(["/qualificacao/<string:slug>", "/inspecao/<string:slug>",
                  "/retrofit/<string:slug>", "/marsp/<string:slug>"],
                type="http", auth="public", website=False)
    def demo(self, slug, **kw):
        prefix = _prefix()
        if slug not in PREFIXES.get(prefix, ()):
            if prefix == "qualificacao" and slug == "caldeira":
                qs = request.httprequest.query_string.decode("utf-8", "replace")
                url = "/inspecao/caldeira" + ("?" + qs if qs else "")
                return request.redirect(url, code=301, local=True)
            raise request.not_found()
        folder = "marsp-" + slug if prefix == "marsp" else slug
        return request.make_response(_page_html(folder, prefix), headers=[
            ("Content-Type", "text/html; charset=utf-8"),
            ("Cache-Control", "public, max-age=600"),
        ])

    @http.route("/marsp", type="http", auth="public", website=False)
    def marsp_index(self, **kw):
        if request.httprequest.path.endswith("/"):     # Odoo's router ignores the trailing slash
            qs = request.httprequest.query_string.decode("utf-8", "replace")
            return request.redirect("/marsp" + ("?" + qs if qs else ""), code=301, local=True)
        return request.make_response(_page_html("marsp-vitrine", "marsp"), headers=[
            ("Content-Type", "text/html; charset=utf-8"),
            ("Cache-Control", "public, max-age=600"),
        ])

    @http.route(["/qualificacao/<string:slug>/<path:fname>", "/inspecao/<string:slug>/<path:fname>",
                  "/retrofit/<string:slug>/<path:fname>", "/marsp/<string:slug>/<path:fname>"],
                type="http", auth="public", website=False)
    def demo_asset(self, slug, fname, **kw):
        prefix = _prefix()
        allowed = MARSP_FOLDERS if prefix == "marsp" else PREFIXES.get(prefix, ()) + ("_vendor",)
        if slug not in allowed:
            raise request.not_found()
        parts = [p for p in fname.split("/") if p]
        if not parts or any(p in (".", "..") or p.startswith(".") for p in parts):
            raise request.not_found()
        path = get_module_resource(MODULE, "static", "demos", slug, *parts)
        if not path or not os.path.isfile(path):
            raise request.not_found()
        with open(path, "rb") as fh:
            data = fh.read()
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        if path.endswith(".js"):
            ctype = "text/javascript"
        return request.make_response(data, headers=[
            ("Content-Type", ctype),
            ("Cache-Control", "public, max-age=86400"),
        ])
