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
    section_ids = fields.One2many(string='Seções',comodel_name='engc.maintenance_plan.section',inverse_name='maintenance_plan',copy=False)
    periodicity_ids = fields.Many2many(
        string='Periodicidade',comodel_name='engc.maintenance_plan.periodicity'
    )
    instrucion_ids =  fields.One2many(string='instruções',comodel_name='engc.maintenance_plan.instruction',inverse_name='maintenance_plan',copy=False)


    def copy(self, default=None):
        # Agregar codigo de validacion aca
        
        return super(MaintencePlan, self).copy()
    
    def action_open_copy_wizard(self):
        """Abre o wizard para copiar plano de manutenção"""
        self.ensure_one()
        return {
            'name': 'Copiar Plano de Manutenção',
            'type': 'ir.actions.act_window',
            'res_model': 'copy.maintenance.plan.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_maintenance_plan_id': self.id,
            }
        }
    
    def get_time_duration(self, periodicitys = [] ):
        result =[]
        time_duration_list = {}
        for rec in self: 
            
            for periodicity in periodicitys:
                if periodicity:
                    instructions = self.env['engc.maintenance_plan.instruction'].search([
                        ('periodicity','=',periodicity.id),
                        ('maintenance_plan','=',rec.id)
                        ])
                else:
                    instructions = self.env['engc.maintenance_plan.instruction'].search([ 
                        ('maintenance_plan','=',rec.id)
                        ])
                time_duration_list[periodicity.name] = sum(instructions.mapped('time_duration'))
                
            result.append(time_duration_list)
        return result
    
    def get_instructions_without_section(self):
        """
        Retorna as instruções do plano que não possuem seção associada.
        Útil para relatórios.
        """
        self.ensure_one()
        return self.instrucion_ids.filtered(lambda i: not i.section).sorted('sequence')
    
    def get_instructions_by_periodicity(self, periodicity):
        """
        Retorna as instruções do plano filtradas por periodicidade.
        
        Args:
            periodicity: registro de engc.maintenance_plan.periodicity
            
        Returns:
            recordset: instruções filtradas e ordenadas por sequência
        """
        self.ensure_one()
        return self.instrucion_ids.filtered(lambda i: i.periodicity.id == periodicity.id if i.periodicity else False).sorted('sequence')
    
    def format_time_duration(self, hours):
        """
        Converte horas decimais para formato hh:mm.
        
        Args:
            hours: float - horas em formato decimal
            
        Returns:
            str: tempo formatado como hh:mm
        """
        if not hours:
            return "00:00"
        h = int(hours)
        m = int((hours - h) * 60)
        return "{:02d}:{:02d}".format(h, m)
    
    def get_section_instructions_grouped_by_periodicity(self, section):
        """
        Retorna as instruções de uma seção agrupadas por periodicidade.
        Ordena os grupos por frequência da periodicidade (menor para maior).
        
        Args:
            section: registro de engc.maintenance_plan.section
            
        Returns:
            list: lista de dicionários, cada um contendo 'name' (nome da periodicidade), 
                  'frequency' (frequência em dias) e 'instructions' (lista de instruções)
        """
        self.ensure_one()
        instructions = section.instrucion_ids.sorted('sequence')
        grouped = {}
        for instruction in instructions:
            if instruction.periodicity:
                periodicity_key = instruction.periodicity.id
                periodicity_name = instruction.periodicity.name
                periodicity_frequency = instruction.periodicity.frequency
            else:
                periodicity_key = 'sem_periodicidade'
                periodicity_name = 'Sem Periodicidade'
                periodicity_frequency = 999999  # Coloca sem periodicidade no final
                
            if periodicity_key not in grouped:
                grouped[periodicity_key] = {
                    'name': periodicity_name,
                    'frequency': periodicity_frequency,
                    'instructions': []
                }
            grouped[periodicity_key]['instructions'].append(instruction)
        
        # Retorna como lista ordenada por frequência (menor para maior)
        result = list(grouped.values())
        result.sort(key=lambda x: x['frequency'])
        return result
    
    def get_total_man_hours_per_year(self):
        """
        Calcula o total de horas de mão de obra por ano para o plano de manutenção.
        
        Para cada instrução, calcula quantas vezes ela será executada por ano baseado
        na periodicidade e multiplica pelo tempo de duração.
        
        Returns:
            float: total de horas de mão de obra por ano
        """
        self.ensure_one()
        total_hours = 0.0
        days_per_year = 365.0
        
        # Agrupa instruções por periodicidade
        instructions_by_periodicity = {}
        for instruction in self.instrucion_ids:
            if instruction.periodicity:
                periodicity_id = instruction.periodicity.id
                frequency = instruction.periodicity.frequency
            else:
                # Instruções sem periodicidade não são contabilizadas
                continue
            
            if periodicity_id not in instructions_by_periodicity:
                instructions_by_periodicity[periodicity_id] = {
                    'frequency': frequency,
                    'instructions': []
                }
            instructions_by_periodicity[periodicity_id]['instructions'].append(instruction)
        
        # Calcula horas por ano para cada periodicidade
        for periodicity_data in instructions_by_periodicity.values():
            frequency = periodicity_data['frequency']
            if frequency > 0:
                # Quantas vezes por ano essa periodicidade ocorre
                times_per_year = days_per_year / frequency
                
                # Soma o tempo de todas as instruções dessa periodicidade
                # Como é uma lista, usamos list comprehension ao invés de .mapped()
                total_time_per_execution = sum(inst.time_duration or 0.0 for inst in periodicity_data['instructions'])
                
                # Total de horas por ano para essa periodicidade
                hours_per_year = total_time_per_execution * times_per_year
                total_hours += hours_per_year
        
        return total_hours


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

    time_duration = fields.Float(string="Tempo (HH:mm)",
        help="Tempo em horas (HH:mm) de duração da tarefa da preventiva")
    
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
        copy=False
        
        
    )
    maintenance_plan  = fields.Many2one(
        string='Plano de Manutenção',
        comodel_name='engc.maintenance_plan',
        
    )

    def action_open_section_form(self):
 
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
