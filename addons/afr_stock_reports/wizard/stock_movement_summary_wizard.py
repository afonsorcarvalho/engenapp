"""Wizard para gerar Sumário de Movimentações de Estoque por Produto."""
import logging
from collections import defaultdict
from datetime import datetime, time

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# Classificação de movimentos por usage das locations
ENTRADA_USAGES_ORIGEM = ('supplier', 'production', 'inventory')
ENTRADA_USAGES_DEST = ('internal',)
ENTRADA_USAGES_DEST_TRANSIT = ('internal', 'transit')

SAIDA_USAGES_ORIGEM = ('internal',)
SAIDA_USAGES_DEST = ('customer', 'production', 'inventory', 'scrap')


class StockMovementSummaryWizard(models.TransientModel):
    """Wizard de filtros e geração do relatório Sumário de Movimentações."""

    _name = 'stock.movement.summary.wizard'
    _description = 'Wizard Sumário de Movimentações de Estoque'

    # --- Período ---
    date_from = fields.Date(
        string='Data inicial',
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string='Data final',
        required=True,
        default=fields.Date.context_today,
    )

    # --- Tipo de movimento ---
    movement_type = fields.Selection(
        [
            ('entrada', 'Apenas Entradas'),
            ('saida', 'Apenas Saídas'),
            ('ambos', 'Entradas e Saídas'),
        ],
        string='Tipo de movimento',
        default='ambos',
        required=True,
    )

    # --- Categorias ---
    category_ids = fields.Many2many(
        'product.category',
        string='Categorias',
        help='Vazio = todas. Inclui subcategorias automaticamente.',
    )

    # --- Armazém / locations ---
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Armazém',
        help='Opcional. Filtra movimentos pelas locations do armazém.',
    )
    location_ids = fields.Many2many(
        'stock.location',
        string='Locations específicas',
        help='Opcional. Substitui o filtro de armazém para granularidade.',
    )
    location_usage = fields.Selection(
        [
            ('internal', 'Físico (internal)'),
            ('virtual', 'Virtual (inventory/production/transit)'),
            ('all', 'Todas'),
        ],
        string='Tipo de location',
        default='internal',
        required=True,
        help='Físico filtra apenas locations usage=internal. '
             'Virtual inclui ajustes/produção/trânsito.',
    )

    # --- Outras opções ---
    include_draft = fields.Boolean(
        string='Incluir não confirmados',
        default=False,
        help='Por padrão filtra apenas movs com state=done. '
             'Se marcado, inclui demais estados (exceto cancelados).',
    )

    # --- Constraints ---

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wiz in self:
            if wiz.date_from and wiz.date_to and wiz.date_from > wiz.date_to:
                raise UserError(_('Data inicial não pode ser maior que data final.'))

    # --- Helpers ---

    def _get_datetime_range(self):
        """Converte date_from/date_to em datetime range inclusivo."""
        self.ensure_one()
        dt_from = datetime.combine(self.date_from, time.min)
        dt_to = datetime.combine(self.date_to, time.max)
        return dt_from, dt_to

    def _get_category_ids_recursive(self):
        """Retorna IDs das categorias selecionadas + descendentes via child_of."""
        self.ensure_one()
        if not self.category_ids:
            return None
        cats = self.env['product.category'].search([
            ('id', 'child_of', self.category_ids.ids),
        ])
        return cats.ids

    def _get_warehouse_location_ids(self):
        """Retorna IDs de locations sob o armazém (via parent_path)."""
        self.ensure_one()
        if not self.warehouse_id:
            return None
        view_loc = self.warehouse_id.view_location_id
        locs = self.env['stock.location'].search([
            ('id', 'child_of', view_loc.id),
        ])
        return locs.ids

    def _filter_location_usage(self, usages):
        """Filtra tupla de usages conforme location_usage selecionado."""
        self.ensure_one()
        if self.location_usage == 'all':
            return usages
        if self.location_usage == 'internal':
            return tuple(u for u in usages if u == 'internal')
        # virtual
        return tuple(u for u in usages if u in ('inventory', 'production', 'transit'))

    def _build_move_domain(self):
        """Constrói domínio para stock.move baseado nos filtros.

        Domínios Odoo: AND é implícito entre tuplas; '&' e '|' usam prefixo
        polonês e cada um aplica aos próximos 2 nós (1 nó = 1 tupla ou 1
        sub-expressão prefixada).
        """
        self.ensure_one()
        dt_from, dt_to = self._get_datetime_range()

        domain = [
            ('date', '>=', dt_from),
            ('date', '<=', dt_to),
        ]
        if self.include_draft:
            domain.append(('state', '!=', 'cancel'))
        else:
            domain.append(('state', '=', 'done'))

        cat_ids = self._get_category_ids_recursive()
        if cat_ids is not None:
            domain.append(('product_id.categ_id', 'in', cat_ids))

        # location_usage filter aplica ao "lado interno" da movimentação
        if self.location_usage == 'internal':
            internal_usages = ['internal']
        elif self.location_usage == 'virtual':
            internal_usages = ['inventory', 'production', 'transit']
        else:
            internal_usages = ['internal', 'inventory', 'production', 'transit']

        # entrada_clause = AND( origem in entrada_origens, destino in internal_usages )
        entrada_clause = [
            '&',
            ('location_id.usage', 'in', list(ENTRADA_USAGES_ORIGEM)),
            ('location_dest_id.usage', 'in', internal_usages),
        ]
        # saida_clause = AND( origem in internal_usages, destino in saida_destinos )
        saida_clause = [
            '&',
            ('location_id.usage', 'in', internal_usages),
            ('location_dest_id.usage', 'in', list(SAIDA_USAGES_DEST)),
        ]

        if self.movement_type == 'entrada':
            domain += entrada_clause
        elif self.movement_type == 'saida':
            domain += saida_clause
        else:
            # ambos: OR das duas cláusulas, cada uma com seu '&' prefixo
            domain += ['|'] + entrada_clause + saida_clause

        # Filtro warehouse/locations: aplica a qualquer perna (origem ou destino)
        loc_filter_ids = None
        if self.location_ids:
            loc_filter_ids = self.location_ids.ids
        elif self.warehouse_id:
            loc_filter_ids = self._get_warehouse_location_ids()

        if loc_filter_ids:
            domain += [
                '|',
                ('location_id', 'in', loc_filter_ids),
                ('location_dest_id', 'in', loc_filter_ids),
            ]

        return domain

    def _classify_move(self, move):
        """Retorna 'entrada', 'saida' ou None para um move.

        Usa os mesmos sets de usages que `_build_move_domain` aplica via SQL,
        garantindo classificação consistente com o filtro.
        """
        if self.location_usage == 'internal':
            internal_usages = {'internal'}
        elif self.location_usage == 'virtual':
            internal_usages = {'inventory', 'production', 'transit'}
        else:
            internal_usages = {'internal', 'inventory', 'production', 'transit'}

        orig = move.location_id.usage
        dest = move.location_dest_id.usage

        is_entrada = (orig in ENTRADA_USAGES_ORIGEM) and (dest in internal_usages)
        is_saida = (orig in internal_usages) and (dest in SAIDA_USAGES_DEST)

        if is_entrada and self.movement_type in ('entrada', 'ambos'):
            return 'entrada'
        if is_saida and self.movement_type in ('saida', 'ambos'):
            return 'saida'
        return None

    def _aggregate_moves(self, moves):
        """Agrega moves por produto somando qtd entrada/saida e valores."""
        self.ensure_one()
        # {product_id: {'entrada_qty': float, 'saida_qty': float}}
        agg = defaultdict(lambda: {'entrada_qty': 0.0, 'saida_qty': 0.0})

        for move in moves:
            kind = self._classify_move(move)
            if not kind:
                continue
            agg[move.product_id.id][kind + '_qty'] += move.product_qty

        # Monta lista de linhas com dados do produto
        product_obj = self.env['product.product']
        lines = []
        for product_id, vals in agg.items():
            product = product_obj.browse(product_id)
            if not product.exists():
                continue
            cost = product.standard_price or 0.0
            entrada_qty = vals['entrada_qty']
            saida_qty = vals['saida_qty']
            line = {
                'product': product,
                'default_code': product.default_code or '',
                'name': product.display_name,
                'category': product.categ_id.complete_name or product.categ_id.name or '',
                'category_id': product.categ_id.id,
                'uom': product.uom_id.name or '',
                'entrada_qty': entrada_qty,
                'saida_qty': saida_qty,
                'saldo': entrada_qty - saida_qty,
                'cost_unit': cost,
                'cost_entrada': entrada_qty * cost,
                'cost_saida': saida_qty * cost,
            }
            lines.append(line)

        # Ordena por categoria, depois nome
        lines.sort(key=lambda l: (l['category'], l['name']))
        return lines

    def _group_by_category(self, lines):
        """Agrupa lines por categoria com subtotais."""
        groups = defaultdict(lambda: {
            'category': '',
            'lines': [],
            'sub_entrada_qty': 0.0,
            'sub_saida_qty': 0.0,
            'sub_cost_entrada': 0.0,
            'sub_cost_saida': 0.0,
        })
        for line in lines:
            cat = line['category'] or 'Sem categoria'
            g = groups[cat]
            g['category'] = cat
            g['lines'].append(line)
            g['sub_entrada_qty'] += line['entrada_qty']
            g['sub_saida_qty'] += line['saida_qty']
            g['sub_cost_entrada'] += line['cost_entrada']
            g['sub_cost_saida'] += line['cost_saida']

        return [groups[k] for k in sorted(groups.keys())]

    def _compute_totals(self, lines):
        """Totais gerais."""
        return {
            'total_entrada_qty': sum(l['entrada_qty'] for l in lines),
            'total_saida_qty': sum(l['saida_qty'] for l in lines),
            'total_cost_entrada': sum(l['cost_entrada'] for l in lines),
            'total_cost_saida': sum(l['cost_saida'] for l in lines),
            'product_count': len(lines),
        }

    # --- Action ---

    def action_print_pdf(self):
        """Gera o PDF do relatório."""
        self.ensure_one()
        report = self.env.ref(
            'afr_stock_reports.action_report_stock_movement_summary'
        )
        return report.report_action(self.ids)
