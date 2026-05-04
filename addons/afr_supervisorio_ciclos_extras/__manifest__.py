{
    'name': 'Supervisório Ciclos - Materiais',
    'version': '16.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Módulo para gerenciamento de materiais esterilizados em ciclos',
    'description': """
        Módulo para gerenciamento de materiais colocados em ciclos de esterilização.
        Permite registrar materiais e suas quantidades em cada ciclo.
    """,
    'author': 'AFR Solucoes Inteligentes',
    'website': 'https://www.afrsolucoesinteligentes.com.br',
    'depends': [
        'base',
        'afr_supervisorio_ciclos',
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_laudo.xml',
        'views/materials_views.xml',
        'views/cycle_materials_lines_views.xml',
        'views/supervisorio_ciclos_extend_views.xml',
        'views/res_company_views.xml',
        'views/menu_views.xml',
        'wizard/wizard_print_laudo_views.xml',
        'reports/supervisorio_ciclo_reports_inherit.xml',
        'reports/laudo_liberacao_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

