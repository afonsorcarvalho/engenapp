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
        "views/os_visita_views.xml",
        "views/qualificacao_os_views.xml",
    ],
    "installable": True,
    "application": False,
}
