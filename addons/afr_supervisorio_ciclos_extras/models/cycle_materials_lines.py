"""Model para linhas de materiais em ciclos de esterilização"""
from odoo import models, fields, api


class CycleMaterialsLines(models.Model):
    """Model para registro de materiais esterilizados em cada ciclo"""
    
    _name = 'afr.supervisorio.cycle.materials.lines'
    _description = 'Linhas de Materiais Esterilizados por Ciclo'
    _order = 'ciclo_id, material_id'
    
    # Relação hierárquica com o ciclo
    ciclo_id = fields.Many2one(
        'afr.supervisorio.ciclos',
        string='Ciclo',
        required=True,
        ondelete='cascade',
        help='Ciclo de esterilização ao qual este material pertence'
    )
    
    # Material esterilizado
    material_id = fields.Many2one(
        'afr.supervisorio.materials',
        string='Material',
        required=True,
        help='Material que foi esterilizado'
    )
    
    # Quantidade
    quantidade = fields.Float(
        string='Quantidade',
        required=True,
        default=1.0,
        help='Quantidade do material esterilizado'
    )
    
    # Unidade de medida
    unidade = fields.Selection([
        ('caixa', 'Caixa'),
        ('unidade', 'Unidade'),
        ('pacote', 'Pacote'),
        ('envelope', 'Envelope'),
        ('kit', 'Kit'),
        ('outro', 'Outro'),
    ],
        string='Unidade',
        required=True,
        default='unidade',
        help='Unidade de medida do material'
    )
    
    # Lote
    lote = fields.Char(
        string='Lote',
        help='Número do lote do material'
    )
    
    # Fabricante (pode ser diferente do fabricante padrão do material)
    fabricante_id = fields.Many2one(
        'res.partner',
        string='Fabricante',
        help='Fabricante do material (se diferente do padrão)'
    )
    
    # Validade
    validade = fields.Date(
        string='Validade',
        help='Data de validade do material'
    )
    
    # Campos relacionados para facilitar visualização
    ciclo_nome = fields.Char(
        related='ciclo_id.name',
        string='Nome do Ciclo',
        readonly=True,
        store=True
    )
    
    material_descricao = fields.Char(
        related='material_id.descricao',
        string='Descrição do Material',
        readonly=True,
        store=True
    )
    
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
        help='Se desmarcado, a linha não aparecerá nas listas'
    )
    
    @api.onchange('material_id')
    def _onchange_material_id(self):
        """Preenche o fabricante automaticamente quando selecionar um material"""
        if self.material_id and self.material_id.fabricante_id:
            self.fabricante_id = self.material_id.fabricante_id
    
    def name_get(self):
        """Sobrescreve o método name_get para exibir informação completa"""
        result = []
        for record in self:
            name = f"{record.material_descricao} - {record.quantidade} {record.unidade}"
            if record.lote:
                name += f" (Lote: {record.lote})"
            result.append((record.id, name))
        return result

