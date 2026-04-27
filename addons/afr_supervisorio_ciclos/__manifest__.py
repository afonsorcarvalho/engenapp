{
    'name': 'Supervisório Ciclos',
    'version': '16.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Módulo para gerenciamento de ciclos',
    'description': """
        Módulo para gerenciamento de ciclos.
        Permite visualizar e analisar dados de ciclos.
    """,
    'author': 'AFR Sistemas',
    'website': 'https://www.afrsistemas.com.br',
    'depends': [
        'base',
        'hr',
        'engc_os',
        'mail',
        'portal',
        'website'
    ],
    'data': [
        'security/supervisorio_groups.xml',
        'security/ir.model.access.csv',
        'data/supervisorio_manager_data.xml',
        'views/hr_employee_views.xml',
        'views/res_config_settings_views.xml',
        'views/portal_templates.xml',
        'views/cycle_features_views.xml',
        'views/cycle_type_views.xml',
        'views/equipments_views.xml',
        'views/indicador_biologico_views.xml',
        'views/wizard_ler_diretorio_ciclos_views.xml',
        'views/supervisorio_ciclos_views.xml',
        'views/menu_views.xml',
        'views/manual_usuario_supervisorio.xml',
        'views/authenticity_check_views.xml',
        'reports/report_txt_to_pdf.xml',
        'reports/supervisorio_ciclo_reports_template.xml',
        'reports/supervisorio_ciclo_reports.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'afr_supervisorio_ciclos/static/src/js/ace_editor.js',
            'afr_supervisorio_ciclos/static/src/xml/ace_editor.xml',
            'afr_supervisorio_ciclos/static/src/css/style.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data_files': [
        ('tools', ['tools/verify_sign.sh'])
    ]
}