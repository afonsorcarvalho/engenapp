# -*- coding: utf-8 -*-
"""
Controller que serve o Manual do Usuário (página de ajuda) em HTML.
Rota: /engc_os/help — apenas usuários logados (auth='user').
"""
import os

from odoo import http
from odoo.http import request


class HelpController(http.Controller):
    """Serve o arquivo HTML do manual do usuário."""

    @http.route("/engc_os/help", type="http", auth="user")
    def help_manual(self, **kw):
        """
        Retorna o conteúdo do manual do usuário (help_manual.html).
        Apenas usuários autenticados podem acessar.
        """
        module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        help_path = os.path.join(module_path, "static", "doc", "help_manual.html")
        try:
            with open(help_path, "r", encoding="utf-8") as f:
                html_content = f.read()
        except (OSError, IOError):
            return request.not_found("Manual não encontrado.")
        return request.make_response(
            html_content,
            headers=[("Content-Type", "text/html; charset=utf-8")],
        )
