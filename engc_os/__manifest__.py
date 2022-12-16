# -*- coding: utf-8 -*-
{
    'name': "engc_os",

    'summary': """
        Ordem de serviços de engenharia clínica""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Afonso Carvalho",
    'website': "http://www.jgma.com.br",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Services',
    'version': '0.1',


    # any module necessary for this one to work correctly
    'depends': ['base', 'mail','hr'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/sequence.xml',
        'views/equipments_views.xml',
        'views/calibration_views.xml',
        'views/calibration_instruments_views.xml',
        'views/os_views.xml',
        'views/menu_views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
}
