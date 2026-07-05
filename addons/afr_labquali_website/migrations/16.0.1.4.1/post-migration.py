# -*- coding: utf-8 -*-
# Roda no -u para 16.0.1.4.1. Migra para conteúdo de builder: remove as views/
# páginas de conteúdo que o módulo enviava antes e publica a homepage.
# Idempotente. (O conteúdo agora é editável no Website Builder, sem upgrade.)
from odoo import api, SUPERUSER_ID
from odoo.addons.afr_labquali_website import _migrate_to_builder_content


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _migrate_to_builder_content(env)
