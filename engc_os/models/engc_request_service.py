from odoo import _, api,  fields, models
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class RequestService(models.Model):
    _name = 'engc.request.service'
    _description = "Solicitação de Serviço"
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
    requester = fields.Char('Requisitante', required=True)
    
    os_ids = fields.One2many(
        'engc.os', 'request_service_id', 'Request Service',
        copy=True)
    os_count = fields.Integer(compute="_compute_os_count")

    def _compute_os_count(self):
        for record in self:
            record.os_count = self.env['engc.os'].search_count(
                [('request_service_id', '=', self.id)])
    os_gerada = fields.Boolean("OS gerada", default=False)
    tecnicos = fields.Many2one('hr.employee', string="Técnico", domain=[("job_id", "=", "TECNICO")],check_company=True)
    equipment_ids = fields.Many2many('engc.equipment', string='Equipamentos', index=True,check_company=True)
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
        vals = []
        for line in equipments:
            vals.append( {
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
                    })
        self.env['dgt_os.os'].create(vals)
            
        self.write({
            'stage_id': 'in_progress',
            'os_gerada': True,
        
            })

        return True

