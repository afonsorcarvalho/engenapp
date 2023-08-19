
from odoo import models, fields, api


class Equipment(models.Model):
    _name = 'engc.equipment'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Equipamento'
    _check_company_auto = True
    _parent_name = "parent_id"
    _parent_store = True

    
    
    parent_left = fields.Integer('Left Parent', index=1)
    parent_right = fields.Integer('Right Parent', index=1)

    STATES = [
       
        ('draft', 'Rascunho'),
        ('in_use', 'Em uso'),
        ('out_of_use', 'Fora de uso'),
        ('useless', 'Inservível'),
        
    ]
    name = fields.Char(compute="_compute_name", store=True)
    apelido = fields.Char("apelido")
    parent_id = fields.Many2one(
        'engc.equipment',index=True,
        string='Equipamento pai',
        )
    child_ids = fields.One2many('engc.equipment', "parent_id", string="Componentes")
    parent_path = fields.Char(index=True, unaccent=False)
    image_1920 = fields.Binary(
        string='avatar',
    )
   
    category_id = fields.Many2one(
        'engc.equipment.category', 'Categoria', required=True, check_company=True)
    state  = fields.Selection(
        string="Status",
        selection=STATES,
        required=True,
        default='in_use',
        tracking=True
    )
    company_id = fields.Many2one(
        string='Instituição', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.company
    )
    client_id = fields.Many2one("res.partner", "Cliente")
    means_of_aquisition_id = fields.Many2one(
        'engc.equipment.means.of.aquisition', 'Meio de Aquisição', required=True,  check_company=True)
    technician_id = fields.Many2one('hr.employee', 'Técnico',check_company=True)
    maintenance_team_id = fields.Many2one(
        'engc.equipment.maintenance.team', 'Equipe de Manutenção',check_company=True)
    section_id =  fields.Many2one(
        'engc.equipment.section',
        string='Departamento'    )
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
    
    calibrations_ids = fields.One2many(
        string="Calibrações",
        comodel_name='engc.calibration',
        inverse_name="equipment_id",
        help="Calibrações e ensaios do equipamentos.",
    )
    oses = fields.One2many(
        string='Ordens de serviço',
        comodel_name='engc.os',
        inverse_name='equipment_id',
       
       
        
    )

    picture_ids = fields.One2many('engc.equipment.pictures', 'equipment_id', "fotos")
    # relatorios = fields.One2many(
    #     'engc.os.relatorio.servico', 'equipment_id', u'Relatórios',
    #     copy=True, 
    #     readonly=False,
    #     check_company=True,
    #     tracking=True)
    
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
                record.name = record.category_id.name + " " + record.model + " " + record.serial_number + " "  + record.marca_id.name
    
    
    

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
    
    '''
        Açao pra colocar equipamento em uso
    '''

    def action_in_use(self):
        for rec in self:
            rec.write({
                'state':'in_use'
            })

    def action_useless(self):
        for rec in self:
            rec.write({
                'state':'useless'
            })
    def action_out_of_use(self):
        for rec in self:
            rec.write({
                'state':'out_of_use'
            })


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
        default=lambda self: self.env.company
    )
    


class Location(models.Model):
    _name = 'engc.equipment.location'
    _description = "Localização dos equipamentos"

    name = fields.Char('Local')
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.company
    )
    


class Situation(models.Model):
    _name = 'engc.equipment.situation'
    _description = "Situação dos equipamentos"

    name = fields.Char('Situação')
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.company
    )
    
    _sql_constraints = [

        ('situation_uniq', 'unique (name,company_id)', 'O nome já existe !')

    ]
class Marca(models.Model):
    _name = 'engc.equipment.marca'
    _description = "Marca dos equipamentos"

    name = fields.Char('Marca')
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.company
    )
    
 
    _sql_constraints = [

        ('situation_uniq', 'unique (name,company_id)', 'O nome já existe !')

    ]


class MeansOfAquisition(models.Model):
    _name = 'engc.equipment.means.of.aquisition'
    _description = "Meio de Aquisição dos equipamentos"

    name = fields.Char('Meio de Aquisição')
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.company
    )
class EquipmentsSection(models.Model):
    _name = 'engc.equipment.section'
    _description = "setor do local equipamentos"
    

    name = fields.Char('Nome no setor')
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.company
    )
    description = fields.Text('Descrição')
    section_parent  = fields.Many2one(
        'engc.equipment.section',
        string='Setor Pai',
        )

class EquipmentsPictures(models.Model):
    _name = 'engc.equipment.pictures'
    _description = "Fotos dos equipamentos"

    name = fields.Char('Título da foto')
    description = fields.Text('Descrição da foto')

    
    equipment_id = fields.Many2one(
        string='Equipamento', 
        comodel_name='engc.equipment', 
        required=True, 
       
    )

    picture = fields.Binary(string="Foto", 
    required=True
     )
    

   

