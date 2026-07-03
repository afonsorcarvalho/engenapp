# -*- coding: utf-8 -*-
# Roda no -u para 16.0.1.3.2. O post_init_hook só roda no INSTALL; esta migration
# garante o mesmo estado no UPGRADE: publica a homepage e remove páginas demo
# concorrentes em /our-services. Idempotente.
from odoo import api, SUPERUSER_ID
from odoo.addons.afr_labquali_website import _ensure_labquali_pages


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _ensure_labquali_pages(env)
