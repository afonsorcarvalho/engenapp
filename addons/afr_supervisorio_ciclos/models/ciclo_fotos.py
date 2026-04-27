# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class CicloFotos(models.Model):
    """
    Modelo para armazenar fotos dos ciclos de esterilização.
    
    Permite associar múltiplas fotos a um ciclo, cada uma com título e legenda.
    """
    _name = 'afr.ciclo.fotos'
    _description = 'Fotos do Ciclo'
    _order = 'sequence, id desc'
    
    # Relacionamento com o ciclo
    ciclo_id = fields.Many2one(
        'afr.supervisorio.ciclos',
        string='Ciclo',
        required=True,
        ondelete='cascade',
        help='Ciclo ao qual esta foto pertence'
    )
    
    # Sequência para ordenação
    sequence = fields.Integer(
        string='Sequência',
        default=10,
        help='Ordem de exibição das fotos'
    )
    
    # Título da foto
    titulo = fields.Char(
        string='Título',
        required=True,
        help='Título descritivo da foto'
    )
    
    # Legenda da foto
    legenda = fields.Text(
        string='Legenda',
        help='Descrição detalhada da foto'
    )
    
    # Imagem
    imagem = fields.Binary(
        string='Imagem',
        required=True,
        help='Arquivo de imagem'
    )
    
    # Nome do arquivo
    nome_arquivo = fields.Char(
        string='Nome do Arquivo',
        help='Nome original do arquivo'
    )
    
    # Data de criação
    data_criacao = fields.Datetime(
        string='Data de Criação',
        default=fields.Datetime.now,
        readonly=True,
        help='Data em que a foto foi adicionada'
    )
    
    # Usuário que criou
    usuario_criacao = fields.Many2one(
        'res.users',
        string='Usuário',
        default=lambda self: self.env.user,
        readonly=True,
        help='Usuário que adicionou a foto'
    )
    
    # Empresa
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        default=lambda self: self.env.company,
        required=True
    )
