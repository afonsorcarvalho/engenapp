# -*- coding: utf-8 -*-
{
    "name": "LabQuali Menu Simplificado",
    "summary": "Simplifica o menu principal para o perfil Operador LabQuali",
    "description": """
Cria os grupos 'Operador LabQuali' e 'Menu Completo' e re-gateia os menus
de topo desnecessários (Discuss, Calendar, Dashboards, Website, Apps,
Inventory) para que apenas usuários com 'Menu Completo' (administradores)
os vejam. Operadores ficam com um menu limpo: Engenharia Clínica, Contatos,
Vendas, Qualificações, Faturamento e Funcionários.

Não altera permissões de acesso a modelos — apenas visibilidade de menu.
""",
    "version": "16.0.1.0.0",
    "author": "AFR Sistemas",
    "website": "https://afrsistemas.com.br",
    "license": "LGPL-3",
    "category": "Tools",
    "depends": [
        "base",
        "mail",
        "calendar",
        "stock",
        "website",
        "spreadsheet_dashboard",
    ],
    "data": [
        "security/labquali_menu_groups.xml",
        "views/menu_gating.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
