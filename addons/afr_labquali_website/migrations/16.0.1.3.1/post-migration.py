# -*- coding: utf-8 -*-
# Roda no -u para 16.0.1.3.0. Garante que a página /our-services servida seja a
# do módulo (servicos_page), despublicando qualquer página demo concorrente do
# tema. Necessário no upgrade (o post_init_hook só roda no install). Idempotente.
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    ours_view = env.ref("afr_labquali_website.servicos_page_view", raise_if_not_found=False)
    ours_page = env.ref("afr_labquali_website.servicos_page", raise_if_not_found=False)
    pages = env["website.page"].with_context(active_test=False).search([("url", "=", "/our-services")])
    for page in pages:
        if ours_page and page.id == ours_page.id:
            continue
        if ours_view and page.view_id.id == ours_view.id:
            continue
        page.is_published = False
