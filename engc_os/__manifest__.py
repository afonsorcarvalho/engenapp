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
    'depends': ['base','base_setup', 'contacts','mail','hr','web_domain_field'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/equipments_views.xml',
        'views/equipment_category_view.xml',
        'views/calibration_views.xml',
        'views/calibration_procedure_views.xml',
        'views/calibration_instruments_views.xml',
        'views/os_views.xml',
        'views/os_relatorio_views.xml',
        'views/preventiva_views.xml',
        'views/maintenance_plan.xml',
        'views/menu_views.xml',
        'views/templates.xml',
        'reports/calibration_certificate_template.xml',
        'reports/assinaturas_template.xml',
        'reports/fotos_template.xml',
        'reports/cliente_equipment_template.xml',
        'reports/os_template.xml',
        'reports/engc_os_reports.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
}
