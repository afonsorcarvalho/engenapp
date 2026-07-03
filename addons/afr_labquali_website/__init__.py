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

    # /our-services: despublica qualquer página demo concorrente (do tema) para
    # que a nossa página do módulo (servicos_page) seja a servida. Idempotente.
    ours = env.ref("afr_labquali_website.servicos_page_view", raise_if_not_found=False)
    ours_page = env.ref("afr_labquali_website.servicos_page", raise_if_not_found=False)
    svc_pages = env["website.page"].with_context(active_test=False).search([("url", "=", "/our-services")])
    for page in svc_pages:
        if ours_page and page.id == ours_page.id:
            continue
        if ours and page.view_id.id == ours.id:
            continue
        page.is_published = False
