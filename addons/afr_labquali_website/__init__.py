# addons/afr_labquali_website/__init__.py
from . import models

# Chaves de views/páginas de CONTEÚDO que o módulo enviava em versões antigas
# (<=16.0.1.3.x). O conteúdo agora vive no Website Builder (editável sem
# upgrade); o módulo só entrega SCSS/footer/imagens. Este cleanup remove os
# leftovers para que o conteúdo de builder (arch da própria página) sirva.
_LEGACY_VIEW_KEYS = ["afr_labquali_website.labquali_homepage", "afr_labquali_website.servicos_page_view"]


def _migrate_to_builder_content(env):
    """Idempotente: publica a homepage e remove views/páginas de conteúdo legadas."""
    View = env["ir.ui.view"].with_context(active_test=False)
    Page = env["website.page"].with_context(active_test=False)

    # 1) remover páginas cujo view é uma view de conteúdo legada
    #    (unlink de website.page também apaga a view associada → usar .exists()
    #     antes de apagar as views restantes para não re-deletar)
    legacy_views = View.search([("key", "in", _LEGACY_VIEW_KEYS)])
    if legacy_views:
        Page.search([("view_id", "in", legacy_views.ids)]).unlink()
        legacy_views.exists().unlink()

    # 2) publicar a homepage (para "/" não cair na loja/404)
    for page in env["website.page"].search([("url", "=", "/")]):
        if page.view_id.key == "website.homepage" and not page.is_published:
            page.is_published = True


def post_init_hook(cr, registry):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    _migrate_to_builder_content(env)
