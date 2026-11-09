"""Scroll-driven explainer pages, one per equipment type.

Each page is a self-contained static build under static/demos/<slug>/ (HTML,
scroll engine, 3D render frames). The page is served at /qualificacao/<slug>
and its assets at /qualificacao/<slug>/<file>.

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
DEMOS = ("autoclave", "termodesinfectora", "estufa", "camara-fria")
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


def _page_html(slug):
    if slug not in _html_cache:
        path = get_module_resource(MODULE, "static", "demos", slug, "index.html")
        with open(path, encoding="utf-8") as fh:
            html = fh.read()
        if _static_dir_is_ours():
            base = _STATIC_PREFIX                      # plain static route: no DB needed, cached by Odoo
        else:
            base = "/qualificacao/"                    # shadowed static dir: serve through this controller
            html = html.replace(_STATIC_PREFIX, base)
        prefix = base + slug + "/"
        _html_cache[slug] = _REL_ATTR.sub(lambda m: m.group(1) + prefix, html)
    return _html_cache[slug]


class LabqualiDemos(http.Controller):

    @http.route("/qualificacao/<string:slug>", type="http", auth="public", website=False)
    def qualificacao_demo(self, slug, **kw):
        if slug not in DEMOS:
            raise request.not_found()
        return request.make_response(_page_html(slug), headers=[
            ("Content-Type", "text/html; charset=utf-8"),
            ("Cache-Control", "public, max-age=600"),
        ])

    @http.route("/qualificacao/<string:slug>/<path:fname>", type="http", auth="public", website=False)
    def qualificacao_demo_asset(self, slug, fname, **kw):
        if slug not in DEMOS + ("_vendor",):
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
