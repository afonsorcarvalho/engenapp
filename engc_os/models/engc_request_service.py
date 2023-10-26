from odoo import _, api,  fields, models
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)



class RequestService(models.Model):
    _name = 'engc.request.service'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True
    _order = 'priority desc, create_date desc'
    
    
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
        default=lambda self: self.env.company
    )
    requester = fields.Char('Requisitante', required=True,default=lambda self: self.env.user.name)

    os_ids = fields.One2many(
        'engc.os', 'request_service_id', 'Request Service',
        copy=True)
    os_gerada = fields.Boolean("OS gerada", default=False)
    tecnicos = fields.Many2one('hr.employee', string="Técnico", domain=[("job_id", "=", "TECNICO")],check_company=True)
    department = fields.Many2one('hr.department', string="Departamento", 
                                 default=lambda self: self._default_department(),
                                 
                                 check_company=True)
    def _default_department(self):
        employee =  self.env['hr.employee'].search([('user_id','=',self.env.user.id)])
        _logger.info(employee)
        return employee.department_id.id


    equipment_ids = fields.Many2many('engc.equipment', 
                                     string='Equipamentos', 
                                     index=True,check_company=True)
    
    equipment_ids_domain = fields.Binary(string='Domain Equipment',compute='_compute_domain_equipment')
    
    @api.depends('department')    
    def _compute_domain_equipment(self):
        for request_service in self:
            _logger.info(f"Departamento:{request_service.department.id}")
            department_ids = request_service.department.get_children_department_ids().mapped('id')
            if department_ids:
                domain = [('department','in',(False,*department_ids))]
            else:
                domain=[]
            request_service.equipment_ids_domain = domain
       
    description = fields.Text('Repair Description')
    state = fields.Selection([('new', 'Nova Solicitação'), ('in_progress', 'Em andamento'),('done', 'Concluído'),('cancel', 'Cancelada')], default="new")
    request_date = fields.Date('Data da Solicitação',tracking=True , default=fields.Date.context_today)
    schedule_date = fields.Date("Scheduled Date")
    close_date = fields.Date('Close Date')
    maintenance_type = fields.Selection([('corrective', 'Corretiva'), ('preventive', 'Preventiva'),('instalacao','Instalação'),('treinamento','Treinamento')], required=True, string='Tipo de Manutenção', default="corrective")
    maintenance_team_id = fields.Many2one(
        'engc.equipment.maintenance.team', 'Equipe de Manutenção',check_company=True)
    priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')], string='Prioridade')
    
    _sql_constraints = [
        ('name', 'unique (name)', 'The name of the Service Request must be unique!'),
    ]
    def action_gera_os(self):
        if not self.tecnicos:
            raise UserError(_("Para gerar OS é necessário o campo Técnico preenchido"))
        args = self.company_id and [('company_id', '=', self.company_id.id)] or []
        warehouse = self.env['stock.warehouse'].search(args, limit=1)
        
        equipments = self.equipments
        
        for line in equipments:
            vals = {
                    'origin': self.name,
                    'cliente_id': self.cliente_id.id,
                    'date_scheduled': self.schedule_date,
                    'date_execution': self.schedule_date,
                    'maintenance_type': self.maintenance_type,
                    'description':self.description,
                    'contact_os': self.contact_os,
                    'equipment_id':line.id,
                    'request_id':self.id,
                    'priority':self.priority,
                    'tecnicos_id': [(4, self.tecnicos.id)]
                    }
            self.env['dgt_os.os'].create(vals)
            
        self.write({
            'stage_id': 'in_progress',
            'os_gerada': True,
        
            })

        return True

