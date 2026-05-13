{
    'name': 'AFR Stock Reports',
    'version': '16.0.1.0.0',
    'category': 'Inventory/Reporting',
    'summary': 'Relatórios customizados de inventário para reprocessamento e esterilização',
    'description': """
        Coleção de relatórios customizados de estoque para empresas de
        reprocessamento e esterilização de materiais hospitalares.

        Relatórios disponíveis:
          1. Sumário de Movimentações por Produto (entrada/saída por período)
          2. Curva ABC de Consumo
          3. Snapshot de Estoque com Valuation
          4. Slow Movers
          5. Reabastecimento Sugerido
          6. Ajustes de Inventário
          7. Lotes Vencendo / Vencidos
          8. Giro de Estoque (Turnover)
          9. Balanço Entrada vs Saída
         10. Histórico Detalhado de Produto
         11. Materiais Descartados (Scrap)
    """,
    'author': 'AFR Soluções Inteligentes',
    'website': 'https://www.afrsolucoesinteligentes.com.br',
    'depends': [
        'base',
        'stock',
        'product',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/paperformat.xml',
        'wizard/stock_movement_summary_wizard_views.xml',
        'reports/stock_movement_summary_report.xml',
        'reports/stock_movement_summary_template.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
