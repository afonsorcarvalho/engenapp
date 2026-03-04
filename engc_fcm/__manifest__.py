# -*- coding: utf-8 -*-
{
    'name': "Engc FCM - Push Notifications (Firebase)",
    'summary': "Registro de token FCM e push para Solicitação de Serviço, Ordem de Serviço e Relatório de Atendimento.",
    'description': """
        Integração com Firebase Cloud Messaging (FCM) para o app mobile Flutter.
        - Campo fcm_token em res.users e método register_fcm_token para o app registrar o token após login.
        - Push ao criar/atualizar: Solicitação de Serviço (engc.request.service), Ordem de Serviço (engc.os),
          Relatório de Atendimento (engc.os.relatorios). Inclui data programada e data conclusão quando aplicável.
        - Grupos de notificação por tipo; FCM HTTP v1 com Service Account (OAuth2).
        Ver README para configurar credenciais e grupos.
    """,
    'author': "Afonso Carvalho",
    'website': "http://www.jgma.com.br",
    'category': 'Services',
    'version': '0.1',
    'license': 'LGPL-3',
    'odoo': '16.0',
    'external_dependencies': {
        'python': [
            'google-auth',
            'requests',
        ],
    },
    'depends': ['base', 'base_setup', 'engc_os'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/res_users_views.xml',
        'views/res_config_settings_views.xml',
        'wizards/engc_fcm_test_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
