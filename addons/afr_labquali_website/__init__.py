# addons/afr_labquali_website/__init__.py
from . import models


def post_init_hook(cr, registry):
    """Garante que a homepage ("/", view key website.homepage) esteja publicada.

    O conteúdo LabQuali é injetado via herança de website.homepage, então a página
    servida em "/" é a própria homepage padrão. Em alguns ambientes o bootstrap
    deixou essa página despublicada (is_published=f) — o que faria o visitante
    anônimo receber 404. Aqui publicamos todas as páginas em "/" cuja view tenha
    key 'website.homepage'. Idempotente.
    """
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    pages = env["website.page"].search([("url", "=", "/")])
    for page in pages:
        if page.view_id.key == "website.homepage" and not page.is_published:
            page.is_published = True
