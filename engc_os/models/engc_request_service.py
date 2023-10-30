from odoo import _, api,  fields, models
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)



class RequestService(models.Model):
    _name = 'engc.request.service'
    _description = "Solicitação de Serviço"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True
    _order = 'priority desc, create_date desc'
    
    WHO_EXECUTOR_SELECTION = [
        ('3rd_party', 'Terceirizada'),
        ('own', 'Própria'),
    ]
    
    name = fields.Char(
        'Requisição Cod.',
        default=lambda self: _('New'), index='trigram',
        copy=False, required=True,
        readonly=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        """Salva ou atualiza os dados no banco de dados"""
        for vals in vals_list:
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_company(self.company_id.id).next_by_code(
                    'engc.service_request_sequence') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('engc.service_request_sequence') or _('New')
            

        result = super(RequestService, self).create(vals)
        return result
    company_id = fields.Many2one(
        string='Instituição', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.company,
        tracking=True
    )
    @api.onchange('company_id')
    def onchange_company_id(self):
        if self.state not in ['new']:
            raise UserError("Não é possível mudar instituição depois de criada. Cancele esta solicitação e crie outra")
        self.department = None
        self.equipment_ids = None
        self.maintenance_team_id = None
        self.tecnicos = None
    
    requester = fields.Char('Requisitante', required=True,default=lambda self: self.env.user.name)

    os_ids = fields.One2many(
        'engc.os', 'request_service_id', 'Request Service',
        copy=True)
    os_count = fields.Integer(compute="_compute_os_count")

    def _compute_os_count(self):
        for record in self:
            record.os_count = self.env['engc.os'].search_count(
                [('request_service_id', '=', self.id)])
    os_gerada = fields.Boolean("OS gerada", default=False)
    tecnicos = fields.Many2one('hr.employee', string="Técnico", check_company=True)
    department = fields.Many2one('hr.department', string="Departamento", 
                                 default=lambda self: self._default_department(),
                                 
                                 check_company=True)
    def _default_department(self):
        employee =  self.env['hr.employee'].search([('user_id','=',self.env.user.id)])
        _logger.info(employee)
        return employee.department_id.id


    equipment_ids = fields.Many2many('engc.equipment', 
                                     string='Equipamentos', 
                                     index=True,check_company=True, 
                                     required=True
                                     )
    
    equipment_ids_domain = fields.Binary(string='Domain Equipment',compute='_compute_domain_equipment')
    
    @api.depends('department')    
    def _compute_domain_equipment(self):
        for request_service in self:
            _logger.info(f"Departamento:{request_service.department.id}")
            department_ids = request_service.department.get_children_department_ids().mapped('id')
            if department_ids:
                domain = ['&',('department','in',(False,*department_ids)),('company_id','=', request_service.company_id.id)]
            else:
                domain=[('company_id','=', request_service.company_id.id)]
            request_service.equipment_ids_domain = domain
       
    description = fields.Text('Repair Description')
    state = fields.Selection([('new', 'Nova Solicitação'), ('in_progress', 'Em andamento'),('done', 'Concluído'),('cancel', 'Cancelada')], default="new",tracking=True)
    request_date = fields.Date('Data da Solicitação',required=True,tracking=True , default=fields.Date.context_today)
    schedule_date = fields.Date("Scheduled Date",
    required=True,tracking=True
    )
    close_date = fields.Date('Close Date')
    maintenance_type = fields.Selection([('corrective', 'Corretiva'), ('preventive', 'Preventiva'),('instalacao','Instalação'),('treinamento','Treinamento')], required=True, string='Tipo de Manutenção', default="corrective")
    who_executor = fields.Selection(WHO_EXECUTOR_SELECTION, string='Manutenção',
                             copy=False, tracking=True 
                            )
    maintenance_team_id = fields.Many2one(
        'engc.equipment.maintenance.team', 'Equipe de Manutenção',check_company=True)
    priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')], string='Prioridade')
    
    _sql_constraints = [
        ('name', 'unique (name)', 'The name of the Service Request must be unique!'),
    ]
    
    def _check_validation_field(self):
        
        fields_not_validate = []
        if not self.tecnicos:
            fields_not_validate.append('Técnicos')
            
        if not self.who_executor:
            fields_not_validate.append('Manutenção')
              
        if fields_not_validate:   
           raise UserError(_(f"Para gerar OS é necessário que os campos abaixo estejam preenchidos:  {[field for field in fields_not_validate] }"))
        return True

    
    def action_go_os(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ordem de Serviços'),
            'view_mode': 'tree,form',
            'res_model': 'engc.os',
            'domain': [('request_service_id', '=', self.id)],
            'target': 'current',
            'context': {
                'create': False,
                'delete': False,
                
                
            },
        }
    
    def action_gera_os(self):
        self._check_validation_field()
       
        args = self.company_id and [('company_id', '=', self.company_id.id)] or []
        warehouse = self.env['stock.warehouse'].search(args, limit=1)
        
        equipments = self.equipment_ids
        vals = []

        for line in equipments:
            vals.append( {
                    'origin': self.name,
                    #'client_id': self.client_id or None,
                    'date_scheduled': self.schedule_date,
                    'date_execution': self.schedule_date,
                    'date_request': self.request_date,
                    'company_id': self.company_id.id,
                    'maintenance_type': self.maintenance_type,
                    'problem_description':self.description,
                    'solicitante': self.requester,
                    'equipment_id':line.id,
                    'request_service_id':self.id,
                    'priority':self.priority,
                    'who_executor':self.who_executor,
                    'tecnico_id': self.tecnicos.id
                    })
        _logger.info(f"Vals: {vals}")
        result = self.env['engc.os'].create(vals)
        _logger.info(f"Resultado: {result}")
        if not result:    
            raise UserError("Erro ao gerar OS")
        self.write({
             'state': 'in_progress',
             'os_gerada': True,
        
             })
        

        return self.action_go_os()

