# addons/afr_labquali_website/__init__.py
from . import models


def _ensure_labquali_pages(env):
    """Garante que as páginas LabQuali sejam as servidas. Idempotente.

    1) Publica a homepage ("/", view key website.homepage) — o conteúdo LabQuali
       é injetado por herança de website.homepage; se a página em "/" estiver
       despublicada, o visitante anônimo cai na loja/404.
    2) /our-services: REMOVE qualquer página demo concorrente (do tema). Não
       basta despublicar: uma página website-específica despublicada ainda é
       casada primeiro pelo _serve_page e devolve 404, sem cair na nossa página
       genérica publicada. Por isso deletamos as concorrentes.
    """
    # 1) publicar homepage
    for page in env["website.page"].search([("url", "=", "/")]):
        if page.view_id.key == "website.homepage" and not page.is_published:
            page.is_published = True

    # 2) remover páginas demo concorrentes em /our-services
    ours_view = env.ref("afr_labquali_website.servicos_page_view", raise_if_not_found=False)
    ours_page = env.ref("afr_labquali_website.servicos_page", raise_if_not_found=False)
    competitors = env["website.page"].with_context(active_test=False).search([("url", "=", "/our-services")])
    for page in competitors:
        if ours_page and page.id == ours_page.id:
            continue
        if ours_view and page.view_id.id == ours_view.id:
            continue
        page.unlink()


def post_init_hook(cr, registry):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    _ensure_labquali_pages(env)
