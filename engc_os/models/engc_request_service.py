from odoo import _, api,  fields, models
from odoo.exceptions import UserError

import logging
import random

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
            

        result = super(RequestService, self).create(vals_list)
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
    # Datas como datetime para compatibilidade com engc.os (date_request, date_scheduled)
    # e registro de data/hora. Consumidores: action_gera_os (engc.os), finish_request/write (close_date).
    request_date = fields.Datetime(
        'Data da Solicitação',
        required=True,
        tracking=True,
        default=fields.Datetime.now,
    )
    schedule_date = fields.Datetime(
        'Data Programada',
        tracking=True,
    )
    close_date = fields.Datetime('Data de Conclusão')
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
        """Gera OS a partir da solicitação. Repassa request_date/schedule_date (Datetime) para engc.os.
        Se Técnico ou Manutenção não estiverem preenchidos: define Manutenção = Própria e Técnico = usuário
        (hr.employee do user_id); se o usuário não tiver funcionário, usa um membro aleatório da equipe de manutenção.
        Caso não tenha data programada (schedule_date), utiliza a data atual da geração.
        Solicitação cancelada não pode gerar OS.
        """
        self.ensure_one()
        if self.state == 'cancel':
            raise UserError(
                _("Uma solicitação de atendimento cancelada não pode gerar OS. "
                  "Reabra ou crie uma nova solicitação para gerar ordem de serviço.")
            )
        if not self.tecnicos or not self.who_executor:
            write_vals = {'who_executor': 'own'}
            if not self.tecnicos:
                employee = self.env['hr.employee'].sudo().search(
                    [('user_id', '=', self.env.user.id)], limit=1
                )
                if employee:
                    write_vals['tecnicos'] = employee.id
                elif self.maintenance_team_id and hasattr(self.maintenance_team_id, 'members') and self.maintenance_team_id.members:
                    # Usuário sem funcionário: escolhe aleatoriamente um técnico da equipe de manutenção
                    members = self.maintenance_team_id.members
                    chosen = random.choice(members)
                    write_vals['tecnicos'] = chosen.id
                    _logger.info(
                        "Gerar OS: usuário sem funcionário vinculado; técnico definido da equipe %s: %s",
                        self.maintenance_team_id.name if hasattr(self.maintenance_team_id, 'name') else "",
                        chosen.name if hasattr(chosen, 'name') else "",
                    )
            self.write(write_vals)
        self._check_validation_field()
        equipments = self.equipment_ids
        vals = []

        # Se não houver data programada, utiliza a data/hora atual
        schedule_date = self.schedule_date or fields.Datetime.now()

        for line in equipments:
            vals.append({
                'origin': self.name,
                # 'client_id': self.client_id or None,
                'date_scheduled': schedule_date,
                'date_execution': schedule_date,
                'date_request': self.request_date,
                'company_id': self.company_id.id,
                'maintenance_type': self.maintenance_type,
                'problem_description': self.description,
                'solicitante': self.requester,
                'equipment_id': line.id,
                'request_service_id': self.id,
                'priority': self.priority,
                'who_executor': self.who_executor,
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

    def finish_request(self):
        """
        Finaliza a solicitação de serviço e registra a data de conclusão.
        """
        self.write({
            'state': 'done',
            'close_date': fields.Datetime.now(),
        })
    
    def write(self, vals):
        """
        Sobrescreve o método write para preencher automaticamente a data de conclusão
        quando o estado for alterado para 'done'.
        """
        # Se o estado está sendo alterado para 'done' e não há data de conclusão, preenche automaticamente
        if 'state' in vals and vals.get('state') == 'done':
            for record in self:
                if not record.close_date:
                    vals['close_date'] = fields.Datetime.now()
        
        return super(RequestService, self).write(vals)

