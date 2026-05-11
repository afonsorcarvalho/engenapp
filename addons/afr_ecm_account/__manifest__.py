{
    'name': 'AFR ECM — Bridge Accounting',
    'version': '16.0.1.0.0',
    'category': 'Document Management',
    'summary': 'Integra afr_ecm com account.move via OCA account_dms_field',
    'author': 'Engenapp',
    'license': 'LGPL-3',
    'depends': [
        'afr_ecm',
        'account_dms_field',
    ],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
