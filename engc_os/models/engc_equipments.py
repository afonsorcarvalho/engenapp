
from odoo import models, fields, api


class Equipment(models.Model):
    _name = 'engc.equipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Equipamento'
    _check_company_auto = True

    name = fields.Char(compute="_compute_name", store=True)
    category_id = fields.Many2one(
        'engc.equipment.category', 'Categoria', required=True, check_company=True)
       
    company_id = fields.Many2one(
        string='Instituição', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    
    situation_id = fields.Many2one(
        'engc.equipment.situation', 'Situação', required=True)
    means_of_aquisition_id = fields.Many2one(
        'engc.equipment.means.of.aquisition', 'Meio de Aquisição', required=True,  check_company=True)
    technician_id = fields.Many2one('hr.employee', 'Técnico',check_company=True)
    maintenance_team_id = fields.Many2one(
        'engc.equipment.maintenance.team', 'Equipe de Manutenção',check_company=True)
    location_id = fields.Many2one(
        'engc.equipment.location', 'Local de Uso', required=True, check_company=True)
    marca_id = fields.Many2one('engc.equipment.marca', 'Marca', required=True)
   
    partner_reference = fields.Char('Referência de Fornecedor')
    model = fields.Char('Modelo', required=True
    )
    serial_number = fields.Char('Número de Série', required=True)
    anvisa_code = fields.Char('Reg Anvisa')
    tag = fields.Char('Tag')
    patrimony = fields.Char('Patrimonio')
    manufacturing_date = fields.Date('Data de Fabricação')
    instalation_date = fields.Date('Date de Instalação')
    acquisition_date = fields.Date('Date de Aquisição')
    warranty = fields.Date('Garantia')
    extended_warranty = fields.Date('Garantia Extendida')
    invoice_document = fields.Binary('Nota Fiscal')
    next_maintenance = fields.Date('Próxima Manutenção Preventiva')
    period = fields.Integer('Frequência de Manutenção')
    
    duration = fields.Float('Duração da Manutenção')
    note = fields.Text()
    oses = fields.One2many(
        string='Ordens de serviço',
        comodel_name='engc.os',
        inverse_name='equipment_id',
        check_company=True,
        store=False,
        
    )

    picture_ids = fields.One2many('engc.equipment.pictures', 'equipment_id', "fotos")
    # relatorios = fields.One2many(
    #     'engc.os.relatorio.servico', 'equipment_id', u'Relatórios',
    #     copy=True, 
    #     readonly=False,
    #     check_company=True,
    #     track_visibility=True)
    
    _sql_constraints = [
        ('serial_marca_company_id_no_uniq',
         'unique (serial_number,marca_id)',
         'Número de série para cada fabricante deve ser único!')
    ]

    
    
      
    
    @api.depends('category_id','model','marca_id','serial_number')
    def _compute_name(self):
        
        for record in self:
            if not record.category_id.name or not record.model or not record.marca_id.name or not record.serial_number:
                record.name = ""
            else:
                record.name = record.category_id.name + " " + record.model + " " + record.marca_id.name + " "  + record.serial_number
    
    
    

    # def name_get(self):
    #     result = []
    #     for record in self:
    #         if record.name and record.serial_number:
    #             result.append((record.id, str(record.id) + '/' +
    #                            record.name + '/' + record.serial_number))
    #         if record.name and not record.serial_number:
    #             result.append((record.id, record.name))
    #     return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []

        if operator == 'ilike' and not (name or '').strip():
            recs = self.search([] + args, limit=limit)
        elif operator in ('ilike', 'like', '=', '=like', '=ilike'):
            recs = self.search(['|', '|', ('name', operator, name), (
                'id', operator, name), ('serial_number', operator, name)] + args, limit=limit)

        return recs.name_get()


class Category(models.Model):
    _name = 'engc.equipment.category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Categoria de Equipamento'
    _check_company_auto = True

    name = fields.Char()
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    
    responsibles = fields.Many2many('res.users', string='Responsáveis')
    note = fields.Text()
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
    category_id = fields.Many2one('engc.equipment.category', 
    company_dependent=True
    )
    sequence = fields.Integer(string='Sequence', default=10)
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    


class MaintenanceTeam(models.Model):
    _name = 'engc.equipment.maintenance.team'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Equipe de Manutenção'
    _check_company_auto = True

    name = fields.Char()
    team_members = fields.Many2many('hr.employee', string='Membros', 
    company_dependent=True
    )
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    


class Location(models.Model):
    _name = 'engc.equipment.location'
    _description = "Localização dos equipamentos"

    name = fields.Char('Local')
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    


class Situation(models.Model):
    _name = 'engc.equipment.situation'
    _description = "Situação dos equipamentos"

    name = fields.Char('Situação')
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    
    _sql_constraints = [

        ('situation_uniq', 'unique (name,company_id)', 'O nome já existe !')

    ]
class Marca(models.Model):
    _name = 'engc.equipment.marca'
    _description = "Marca dos equipamentos"

    name = fields.Char('Marca')
    
 
    _sql_constraints = [

        ('situation_uniq', 'unique (name)', 'O nome já existe !')

    ]


class MeansOfAquisition(models.Model):
    _name = 'engc.equipment.means.of.aquisition'
    _description = "Meio de Aquisição dos equipamentos"

    name = fields.Char('Meio de Aquisição')
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )

class EquipmentsPictures(models.Model):
    _name = 'engc.equipment.pictures'
    _description = "Fotos dos equipamentos"

    name = fields.Char('Descrição da foto')

    
    equipment_id = fields.Many2one(
        string='Equipamento', 
        comodel_name='engc.equipment', 
        required=True, 
       
    )

    picture = fields.Binary(string="Foto", 
    required=True
     )
    

   

