# -*- coding: utf-8 -*-
{
    "name": "AFR Qualificação - Agendamento de Visitas",
    "version": "16.0.1.0.0",
    "category": "Services/Qualificação",
    "summary": "Agendamento de visitas de campo das OS de qualificação",
    "author": "AFR",
    "license": "LGPL-3",
    "depends": ["afr_qualificacao"],
    "data": [
        "security/ir.model.access.csv",
        "views/suggest_visitas_wizard_views.xml",
        "views/os_visita_views.xml",
        "views/qualificacao_os_views.xml",
        "views/visita_board_action.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "afr_qualificacao_agendamento/static/src/board/visita_board.scss",
            "afr_qualificacao_agendamento/static/src/board/visita_board.xml",
            "afr_qualificacao_agendamento/static/src/board/visita_board.js",
        ],
    },
    "installable": True,
    "application": False,
}
