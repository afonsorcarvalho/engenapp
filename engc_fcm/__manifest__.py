# -*- coding: utf-8 -*-
{
    'name': "Engc FCM - Push Notifications (Firebase)",
    'summary': "Registro de token FCM em usuários e envio de push ao criar Solicitação de Serviço.",
    'description': """
        Integração com Firebase Cloud Messaging (FCM) para o app mobile Flutter.
        - Campo fcm_token em res.users e método register_fcm_token para o app registrar o token após login.
        - Ao criar um registro em engc.request.service (Solicitação de Serviço), envia notificação FCM
          para usuários elegíveis (grupo de notificação) com payload data: type, request_service_id, title, body.
        - Utiliza FCM HTTP v1 API com autenticação via Service Account (OAuth2).
        Ver README ou doc do módulo para configurar credenciais (Service Account JSON ou variáveis de ambiente).
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
