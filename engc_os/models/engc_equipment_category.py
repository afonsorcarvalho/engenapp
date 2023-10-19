
from odoo import models, fields
from odoo.addons import decimal_precision as dp

class EngcEquipmentCategory(models.Model):
    _name = 'engc.equipment.category'
    _inherit = ['mail.thread']
    _description = 'Categoria de Equipamento'
   

    name = fields.Char()
    
    
    
    note = fields.Text("Notas",)
    # equipments_id = fields.One2many(
    #     'engc.equipment', 'category_id', string='Equipamentos', 
    #     company_dependent=True
    #     )
    # instructions_id = fields.One2many(
    #     comodel_name='engc.equipment.category.instruction',  inverse_name='category_id'
    #    ,
    #     )
    maintenance_plan = fields.Many2one(
        string='Plano de manutenção',
        comodel_name='engc.maintenance_plan',
        
    )
    
    sequence = fields.Integer(string='Sequence', default=10)


class CategoryInstruction(models.Model):
    _name = 'engc.equipment.category.instruction'
    _description = "Instruções de tarefas para os equipamentos"
    _check_company_auto = True
    _order = 'sequence ASC'
    name = fields.Char('Instrução')
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.company
    )
    sequence = fields.Integer(string='Sequence', default=10)
    category_id = fields.Many2one('engc.equipment.category', 
        
    )
    description = fields.Html("Descrição")
    grupo_id = fields.Many2one(
        string="Grupo",
        comodel_name='engc.equipment.category.instruction.group',
        company_dependent=True,
        ondelete="cascade",
        help="Grupo de instruções para dividir em preventivas em tempos diferentes.",
    )
    tempo_duracao = fields.Float(string="Tempo de duração",
        help="Tempo em minutos de duração da tarefa da preventiva")
    tem_medicao = fields.Boolean(string='Tem medição?')
    grandeza = fields.Many2one(string = 'Grandeza',
        comodel_name='engc.equipment.category.instruction.grandeza', 
        ondelete="set null", help="Grandeza da instrução caso envolva medições",)
    tipo_de_campo = fields.Selection(
        string=u'Tipo de Campo',
        selection=[('Valor', 'float'), ('Checkbox', 'ok'),('Seleção','Selection')]
    )
   

class EngcEquipmentCategoryInstrucionGroup(models.Model):
    """ Grupo de instruções de para tarefas na preventiva relacionada a cada categoria.
    
    """
    _name = 'engc.equipment.category.instruction.group'
    _description = u'Grupo de instruções de preventivas'

    _rec_name = 'name'
    _order = 'name ASC'
    _check_company_auto = True

    name = fields.Char(
        string=u'Grupo',
        required=True
    )   
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.company
    )
    category_id = fields.Many2one(
        string="Categoria de equipamentos",
        comodel_name="engc.equipment.category",
        ondelete="set null",
        company_dependent=True,
        help="Categoria de equipamento a qual pertence o grupo de instruções",
    )   
    periodicity = fields.Integer(string="Periodicidade", help="Tempo em dias para próxima preventiva")
    instruction_type = fields.Selection(
        string="Tipo de instrução",
        selection=[
                ('preventive', 'Preventiva'),
                ('instalation', 'Instalação'),
                ('corrective', 'Corretiva'),
                ('calibration', 'Calibração'),
                ('qualification', 'Qualificação'),
        ],
    )
   
  
  
    sequence = fields.Integer(string='Sequence', default=10)


class CategoryInstrucionPreventivaGrandeza(models.Model):
    """
    Model for Storing Magnitude Categories for Preventive Instructions.

    This model represents the various magnitude categories that can be associated with preventive instructions
    for equipment maintenance. Magnitude categories describe the units in which measurements for preventive
    instructions are taken.

    Attributes:
        _name (str): Technical name of the model.
        _description (str): A brief description of the purpose of the model.
        _rec_name (str): The field used as the record name for the model.
        _order (str): The default sorting order for records in the model.

        name (fields.Char): The name of the magnitude category.
            It serves as a human-readable identifier for each category.

        unidade (fields.Char): The unit associated with the magnitude category.
            For example, this field might hold values like 'KM/h' or 'Joules'.
            It provides information about the measurement unit for preventive instructions.

    Note:
        The model 'CategoryInstrucionPreventivaGrandeza' is designed to store various magnitude categories,
        allowing equipment maintenance instructions to be categorized according to the unit of measurement.

    """

    _name = 'engc.equipment.category.instruction.grandeza'
    _description = u'Grandezas da instruççoes de preventiva'

    _rec_name = 'name'
    _order = 'name ASC'

    name = fields.Char(
        string=u'Nome',
        required=True
       
    )
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.company
    )
    unidade = fields.Char(
        string=u'Unidade',help="Unidade da grandeza. exemplo: KM/h, Joules"

    )


    
    


