
from odoo import models, fields
from odoo.addons import decimal_precision as dp

class EngcEquipmentCategory(models.Model):
    _name = 'engc.equipment.category'
    _inherit = ['mail.thread']
    _description = 'Categoria de Equipamento'
    _check_company_auto = True

    name = fields.Char()
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    
    responsibles = fields.Many2many('res.users', string='Responsáveis',
                    company_dependent=True)
    note = fields.Text("Notas",)
    equipments_id = fields.One2many(
        'engc.equipment', 'category_id', string='Equipamentos', 
        company_dependent=True
        )
    instructions_id = fields.One2many(
        'engc.equipment.category.instruction', 'category_id', 
        company_dependent=True,
        copy=True)
    sequence = fields.Integer(string='Sequence', default=10)


class CategoryInstruction(models.Model):
    _name = 'engc.equipment.category.instruction'
    _description = "Instruções de tarefas para os equipamentos"
    _check_company_auto = True

    name = fields.Char('Instrução')
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    sequence = fields.Integer(string='Sequence', default=10)
    category_id = fields.Many2one('engc.equipment.category', 
        company_dependent=True
    )
    grupo_id = fields.Many2one(
        string="Grupo",
        comodel_name='engc.equipment.category.instruction.group',
        
        ondelete="cascade",
        help="Grupo de instruções para dividir em preventivas em tempos diferentes.",
    )

class EngcEquipmentCategoryInstrucionGroup(models.Model):
    """ Grupo de instruções de para tarefas na preventiva relacionada a cada categoria.
    
    """
    _name = 'engc.equipment.category.instruction.group'
    _description = u'Grupo de instruções de preventivas'

    _rec_name = 'name'
    _order = 'name ASC'

    name = fields.Char(
        string=u'Grupo',
        required=True
    )   
    category_id = fields.Many2one(
        string="Categoria de equipamentos",
        comodel_name="dgt_os.equipment.category",
        ondelete="set null",
        help="Categoria de equipamento a qual pertence o grupo de instruções",
    )   
    periodicity = fields.Integer(string="Periodicidade", help="Tempo em dias para próxima preventiva")
    instruction_type = fields.Selection(
        string="Tipo de instrução",
        selection=[
                ('preventiva', 'Preventiva'),
                ('instalacao', 'Instalação'),
                ('corretiva', 'Corretiva'),
                ('calibracao', 'Calibração'),
        ],
    )
    sequence = fields.Integer(string='Sequence', default=10)


    
    


