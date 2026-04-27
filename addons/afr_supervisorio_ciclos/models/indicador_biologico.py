# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class IndicadorBiologico(models.Model):
    """
    Modelo para cadastro de Indicadores Biológicos utilizados nos ciclos de esterilização ETO.
    
    Armazena informações sobre o lote, marca, modelo e validade dos indicadores biológicos.
    """
    _name = 'afr.indicador.biologico'
    _description = 'Indicador Biológico para Ciclos ETO'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'
    
    # Campo name como lote do indicador biológico
    name = fields.Char(
        string='Lote',
        required=True,
        help='Número do lote do indicador biológico'
    )
    
    # Marca do indicador biológico
    marca = fields.Char(
        string='Marca',
        required=True,
        help='Fabricante do indicador biológico'
    )
    
    # Modelo do indicador biológico
    modelo = fields.Char(
        string='Modelo',
        help='Modelo ou referência do indicador biológico'
    )
    
    # Data de fabricação
    data_fabricacao = fields.Date(
        string='Data de Fabricação',
        help='Data em que o indicador biológico foi fabricado'
    )
    
    # Data de validade
    data_validade = fields.Date(
        string='Data de Validade',
        help='Data de validade do indicador biológico'
    )
    
    # Campo computado para verificar se está vencido
    vencido = fields.Boolean(
        string='Vencido',
        compute='_compute_vencido',
        store=True,
        help='Indica se o indicador biológico está vencido'
    )
    
    # Notas adicionais
    notes = fields.Text(
        string='Observações',
        help='Observações adicionais sobre o indicador biológico'
    )
    
    # Empresa
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        default=lambda self: self.env.company,
        required=True
    )
    
    @api.depends('data_validade')
    def _compute_vencido(self):
        """
        Calcula se o indicador biológico está vencido com base na data de validade.
        """
        hoje = fields.Date.today()
        for record in self:
            if record.data_validade:
                record.vencido = record.data_validade < hoje
            else:
                record.vencido = False
    
    _sql_constraints = [
        ('lote_marca_unique', 'unique(name, marca, company_id)', 
         'Já existe um indicador biológico com este lote e marca para esta empresa!')
    ]

