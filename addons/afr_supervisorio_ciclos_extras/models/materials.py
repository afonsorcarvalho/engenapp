"""Model para gerenciamento de materiais"""
from odoo import models, fields, api


class Materials(models.Model):
    """Model para cadastro de materiais que podem ser esterilizados"""
    
    _name = 'afr.supervisorio.materials'
    _description = 'Materiais para Esterilização'
    _order = 'descricao'
    
    # Campo descrição do material
    descricao = fields.Char(
        string='Descrição',
        required=True,
        help='Descrição do material a ser esterilizado'
    )
    
    # Campo fabricante (relacionamento com res.partner)
    fabricante_id = fields.Many2one(
        'res.partner',
        string='Fabricante',
        help='Fabricante do material'
    )
    
    # Campo para exibir nome do fabricante
    fabricante_nome = fields.Char(
        related='fabricante_id.name',
        string='Nome do Fabricante',
        readonly=True,
        store=True
    )
    
    # Campos de auditoria
    active = fields.Boolean(
        string='Ativo',
        default=True,
        help='Se desmarcado, o material não aparecerá nas listas'
    )
    
    _sql_constraints = [
        ('descricao_fabricante_unique', 
         'unique(descricao, fabricante_id)', 
         'Já existe um material com esta descrição para este fabricante!')
    ]
    
    def name_get(self):
        """Sobrescreve o método name_get para exibir descrição do material"""
        result = []
        for record in self:
            name = record.descricao
            if record.fabricante_nome:
                name = f"{name} ({record.fabricante_nome})"
            result.append((record.id, name))
        return result

