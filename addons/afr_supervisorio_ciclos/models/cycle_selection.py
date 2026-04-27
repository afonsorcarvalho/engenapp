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
    phases_planned = fields.Text(
        string='Fases planejadas (JSON)',
        help='''Mapa fase -> duração em minutos, usado pela barra segmentada do frontend.
        Exemplo:
        {"pre-vacuo": 5, "aquecimento": 12, "esterilizacao": 45, "secagem": 20, "resfriamento": 10}
        A ordem das chaves define a ordem dos segmentos. Quando os nomes coincidirem com as
        chaves de fases_fita_digital do tipo de ciclo, o frontend correlaciona com cycle_statistics_data.'''
    )
