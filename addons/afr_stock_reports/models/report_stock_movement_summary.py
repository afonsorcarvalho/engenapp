"""AbstractModel que prepara dados do relatório Sumário de Movimentações."""
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class ReportStockMovementSummary(models.AbstractModel):
    _name = 'report.afr_stock_reports.report_stock_movement_summary_template'
    _description = 'Report Sumário de Movimentações de Estoque'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizards = self.env['stock.movement.summary.wizard'].browse(docids)
        wizard = wizards[:1]
        if not wizard:
            return {'doc_ids': docids, 'doc_model': 'stock.movement.summary.wizard',
                    'docs': wizards, 'lines': [], 'groups': [], 'totals': {},
                    'filters': {}, 'wizard': False}

        domain = wizard._build_move_domain()
        moves = self.env['stock.move'].search(domain)
        lines = wizard._aggregate_moves(moves)
        groups = wizard._group_by_category(lines)
        totals = wizard._compute_totals(lines)

        filters = {
            'date_from': wizard.date_from,
            'date_to': wizard.date_to,
            'movement_type': dict(wizard._fields['movement_type'].selection).get(
                wizard.movement_type, wizard.movement_type
            ),
            'movement_type_raw': wizard.movement_type,
            'location_usage': dict(wizard._fields['location_usage'].selection).get(
                wizard.location_usage, wizard.location_usage
            ),
            'include_draft': wizard.include_draft,
            'warehouse_name': wizard.warehouse_id.display_name or '',
            'category_names': ', '.join(wizard.category_ids.mapped('complete_name')) or 'Todas',
            'location_names': ', '.join(wizard.location_ids.mapped('complete_name')) or '',
            'company_name': self.env.company.name,
            'company_currency': self.env.company.currency_id,
        }

        return {
            'doc_ids': docids,
            'doc_model': 'stock.movement.summary.wizard',
            'docs': wizards,
            'wizard': wizard,
            'lines': lines,
            'groups': groups,
            'totals': totals,
            'filters': filters,
        }
