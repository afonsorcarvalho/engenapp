from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SupervisorioCicloCaracteristicas(models.Model):
    _name = 'afr.cycle.features'
    _description = 'Ciclo Características'
    
    cycle_type_id = fields.Many2one('afr.cycle.type', string='Tipo de Ciclo')
    name = fields.Char('Nome', required=True)
    description = fields.Text('Descrição')
    active = fields.Boolean('Ativo', default=True)
    tempo_estimado = fields.Float('Tempo Estimado (min)', help='Tempo estimado para o ciclo')
    temperatura = fields.Float('Temperatura (°C)', help='Temperatura alvo para esterilização')
    pressao = fields.Float('Pressão (Bar)', help='Pressão alvo para esterilização')
    
    