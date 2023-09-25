from odoo import _, api, fields, models, tools
class MaintencePlan(models.Model):

    """
    Model for Maintenance Plans.

    This model represents maintenance plans which include sections, periodicities, and instructions.

    Attributes:
        _name (str): The technical name of the model.
        _description (str): A brief description of the purpose of the model.
        _check_company_auto (bool): Indicates whether company check is automatic.
        _order (str): The default sorting order for records in the model.

        name (fields.Char): The name of the maintenance plan.
        company_id (fields.Many2one): The company associated with the maintenance plan.
        objective (fields.Char): The objective of the maintenance plan.
        section_ids (fields.One2many): The related sections of the maintenance plan.
        periodicity_ids (fields.One2many): The related periodicities of the maintenance plan.
        instrucion_ids (fields.One2many): The related instructions of the maintenance plan.

    Note:
        The model 'MaintencePlan' is designed to manage maintenance plans, including sections, periodicities, and instructions.
    """
    
    _name = 'engc.maintenance_plan'
    _description = 'Plano de manutenção'
    _check_company_auto = True


    _order = 'name ASC'

    STATE = [
        ('Criado', 'draft'),
        ('vigente', 'current'),
        ('obsoleto', 'obsolete'),
        ]

    name = fields.Char(
        string=u'Nome',
        required=True
       
    )
    state = fields.Selection( selection=STATE)
    
    company_id = fields.Many2one(
        string='Instituição', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.company
    )
    
    objective = fields.Char("Objetivo")
    
    # field_name_ids = fields.One2many(
    #     string='field_name',
    #     comodel_name='model.name',
    #     inverse_name='inverse_field',
    # )
    
    section_ids = fields.One2many(string='Seções',comodel_name='engc.maintenance_plan.section',inverse_name='maintenance_plan',copy=True)
    #periodicity_ids = fields.One2many(string='Periodicidade',comodel_name='engc.maintenance_plan.periodicity',inverse_name='maintenance_plan')
    
  
    periodicity_ids = fields.Many2many(
        string='Periodicidade',comodel_name='engc.maintenance_plan.periodicity'
    )
    instrucion_ids =  fields.One2many(string='instruções',comodel_name='engc.maintenance_plan.instruction',inverse_name='maintenance_plan',copy=True)

    
 

class MaintencePlanInstruction(models.Model):
    """
    Model for Maintenance Plan Instructions.

    This model represents instructions related to a maintenance plan.

    Attributes:
        _name (str): The technical name of the model.
        _description (str): A brief description of the purpose of the model.
        _order (str): The default sorting order for records in the model.

        name (fields.Char): The name of the instruction.
        maintenace_id (fields.Many2one): The maintenance plan associated with the instruction.
        section (fields.Many2one): The section associated with the instruction.
        periodicity (fields.Many2one): The periodicity associated with the instruction.

    Note:
        The model 'MaintencePlanInstruction' is designed to manage instructions related to maintenance plans.
    """
  
    _name = 'engc.maintenance_plan.instruction'
    _description = u'Seção Plano de manutenção'

    _order = 'sequence ASC'

    name = fields.Char(
        string=u'Nome',
        required=True
       
    )
    sequence = fields.Integer(string='Sequence', default=10)

    time_duration = fields.Float(string="Tempo de duração",
        help="Tempo em minutos de duração da tarefa da preventiva")
    
    maintenance_plan = fields.Many2one(
        'engc.maintenance_plan',
        string='Plano de Manutenção',
        )
    is_measurement = fields.Boolean(string='É medição?', default=False)
    magnitude = fields.Many2one(string = 'Grandeza',comodel_name='engc.maintenance_plan.instruction.magnitude', ondelete="set null", help="Grandeza da instrução caso envolva medições",)
    tipo_de_campo = fields.Selection(
        string=u'Tipo de Campo',
        selection=[('float', 'Valor'), ('checkbox', 'Checkbox'),('selection','Seleção')],
        default='checkbox'
    )

    section = fields.Many2one(
        string='Seção',
        comodel_name='engc.maintenance_plan.section',
    
    )
   

    periodicity = fields.Many2one(
        string='Periodicidade',
        comodel_name='engc.maintenance_plan.periodicity',
       
    )

class MaintencePlanSection(models.Model):
    """
    Model for Maintenance Plan Sections.

    This model represents sections related to a maintenance plan.

    Attributes:
        _name (str): The technical name of the model.
        _description (str): A brief description of the purpose of the model.
        _order (str): The default sorting order for records in the model.

        name (fields.Char): The name of the section.
        maintenance_plan (fields.Many2one): The maintenance plan associated with the section.

    Note:
        The model 'MaintencePlanSection' is designed to manage sections related to maintenance plans.
    """
  
    _name = 'engc.maintenance_plan.section'
    _description = u'Seção Plano de manutenção'

    _order = 'sequence ASC'

    
    name = fields.Char(
        string=u'Nome',
        required=True
       
    )
    sequence = fields.Integer(string='Sequence', default=10)
    instrucion_ids = fields.One2many(
        string='Instruções',
        comodel_name='engc.maintenance_plan.instruction',
        inverse_name = 'section',
        
    )
    maintenance_plan  = fields.Many2one(
        string='Plano de Manutenção',
        comodel_name='engc.maintenance_plan',
        
    )

    def action_open_section_form(self):
 
        #    if self._context['action'] == "agendar":
        #     self.action_agendar()
        #     return

        # if self._context['action'] == "iniciar":
        #     self.action_iniciar()

        # if self._context['action'] == "reiniciar":
        #     self.action_reiniciar()
       
            
            
        res_model = 'engc.maintenance_plan.section'
        view_id = self.env.ref('engc_os.maintenance_plan_instructions_sections_form', False).id
        return {
            'name': ('Seção'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'res_model': res_model, 
            'type': 'ir.actions.act_window',
            'context': {'default_id': self.id,'create': 0},
            'target': 'new',
            'res_id': self.id,
            'nodestroy': True,
            
        }

class MaintencePlanPeriodicity(models.Model):
    """
    Model for Maintenance Plan Periodicities.

    This model represents periodicities related to a maintenance plan.

    Attributes:
        _name (str): The technical name of the model.
        _description (str): A brief description of the purpose of the model.
        _order (str): The default sorting order for records in the model.

        name (fields.Char): The name of the periodicity.
        frequency (fields.Integer): The frequency of the periodicity in days.

    Note:
        The model 'MaintencePlanPeriodicity' is designed to manage periodicities related to maintenance plans.
    """
    _name = 'engc.maintenance_plan.periodicity'
    _description = u'Periodicidade do Plano de manutenção'

    _order = 'sequence ASC'

    name = fields.Char(
        string=u'Nome',
        required=True
       
    )
    sequence = fields.Integer(string='Sequence', default=10)
    frequency =  fields.Integer("Pediodicidade (dias)")
    # maintenance_plan  = fields.Many2one(
    #     string='Plano de Manutenção',
    #     comodel_name='engc.maintenance_plan',
        
    # )


class MaintencePlanInstructionMagnitude(models.Model):
 
   
    _name = 'engc.maintenance_plan.instruction.magnitude'
    _description = u'Grandezas da instruçoes de preventiva'

    _rec_name = 'name'
    _order = 'name ASC'

    name = fields.Char(
        string=u'Nome',
        required=True
       
    )
    
    unit = fields.Char(
        string=u'Unidade',help="Unidade da grandeza. exemplo: KM/h, Joules"

    )


   
  

   


    
