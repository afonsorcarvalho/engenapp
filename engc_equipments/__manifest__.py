# -*- coding: utf-8 -*-
{
    'name': "engc_equipments",

    'summary': """
        Cadastro de equipamentos""",

    'description': """
        Cadastro de equipamentos
    """,

    'author': "Afonso Carvalho",
    'website': "http://www.jgma.com.br",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Services',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','engc_os'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
