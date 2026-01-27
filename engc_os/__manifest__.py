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
    'depends': ['base','base_setup','product', 'contacts','mail','hr','web_domain_field','stock','steril_stock'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/cronograma_weekdays.xml',
        'data/sequence.xml',
        'views/equipment_category_view.xml',
        'views/calibration_views.xml',
        'views/calibration_procedure_views.xml',
        'views/calibration_instruments_views.xml',
        'wizards/application_parts_wizard.xml',
        'views/os_views.xml',
        'views/os_relatorio_views.xml',
        'views/os_relatorio_request_parts_views.xml',
        'views/os_check_list_view.xml',
        'views/request_service_views.xml',
        'views/preventiva_views.xml',
        'views/maintenance_plan.xml',
        'views/templates.xml',
        'wizards/relatorio_atendimento_resumo_wizard.xml',
        'reports/calibration_certificate_template.xml',
        'reports/checklist_template.xml',
        'reports/report_checklist_blank_template.xml',
        'reports/report_relatorio_atendimento_blank_template.xml',
        'reports/report_relatorio_atendimento_resumo_template.xml',
        'reports/assinaturas_template.xml',
        'reports/os_relatorio_pecas_template.xml',
        'reports/fotos_template.xml',
        'reports/cliente_equipment_template.xml',
        'reports/os_template.xml',
        'reports/maintenance_plan_template.xml',
        'reports/cronograma_preventiva_template.xml',
        'reports/equipment_cronograma_template.xml',
        'reports/engc_os_reports.xml',
        'views/equipments_views.xml',
        'views/menu_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'engc_os/static/src/css/weekdays_checkboxes.css',
        ],
    },
    'installable': True,
    'application': True,
}
