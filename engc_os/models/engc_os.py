import time
from datetime import date, datetime, timedelta

from odoo import models, fields,  api, _, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
from odoo import netsvc
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class EngcOs(models.Model):
    _name = 'engc.os'
    _description = 'Ordem de Serviço'
    _inherit = ['mail.thread' ]
    _check_company_auto = True

    _order = 'name'

    STATE_SELECTION = [
        ('draft', 'Criada'),
        ('under_budget', 'Em Orçamento'),
        ('pause_budget', 'Orçamento Pausado'),
        ('wait_authorization', 'Esperando aprovação'),
        ('wait_parts', 'Esperando peças'),
        ('execution_ready', 'Pronta para Execução'),
        ('under_repair', 'Em execução'),
        ('pause_repair', 'Execução Pausada'),
        ('reproved','Reprovada'),
        ('done', 'Concluída'),
        ('cancel', 'Cancelada'),
    ]

    # TODO Transformar o tipo de manutenção em uma classe será que é preciso?
    MAINTENANCE_TYPE_SELECTION = [
        ('corrective', 'Corretiva'),
        ('preventive', 'Preventiva'),
        ('instalacao', 'Instalação'),
        ('treinamento', 'Treinamento'),
        ('preditiva', 'Preditiva'),
        ('qualification', 'Qualificação'),
        ('loan', 'Comodato'),
        ('calibration', 'Calibração'),

    ]

    GARANTIA_SELECTION = [
        ('servico', 'Serviço'),
        ('fabrica', 'Fábrica')
    ]

    WHO_EXECUTOR_SELECTION = [
        ('3rd_party', 'Terceirizada'),
        ('own', 'Própria'),
    ]
   

    @api.model_create_multi
    def create(self, vals_list):
        """Salva ou atualiza os dados no banco de dados"""
        for vals in vals_list:
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_company(self.company_id.id).next_by_code(
                    'engc.os_sequence') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('engc.os_sequence') or _('New')
            

        result = super(EngcOs, self).create(vals)
        return result

    # @api.model
    # def _gera_qr(self):

    #	self.qr = self.name + "\n" + self.cliente_id.name + "\n" + self.equipment_id.name + "-" + self.equipment_id.serial_no



    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='OS. N', required=True, copy=False,
                       readonly=True, index=True, default=lambda self: _('New'))
    company_id = fields.Many2one(
        string='Instituição', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.company
    )
    
    client_id = fields.Many2one("res.partner", "Cliente")

    origin = fields.Char('Source Document', size=64, readonly=True, states={'draft': [('readonly', False)]},
                         help="Referencia ao documento que gerou a ordem de servico.")
    state = fields.Selection(STATE_SELECTION, string='Status',
                             copy=False, default='draft',  tracking=True,
                             help="* The \'Draft\' status is used when a user is encoding a new and unconfirmed repair order.\n"
                             "* The \'Done\' status is set when repairing is completed.\n"
                             "* The \'Cancelled\' status is used when user cancel repair order.")
    who_executor = fields.Selection(WHO_EXECUTOR_SELECTION, string='Manutenção',
                             copy=False, tracking=True, required=True,
                            )
    kanban_state = fields.Selection([('normal', 'In Progress'), ('blocked', 'Blocked'), ('done', 'Ready for next stage')],
                                    string='Kanban State', required=True, default='normal', tracking=True)
   
    priority = fields.Selection([('0', 'Normal'), ('1', "Baixa"),
                                 ('2', "Alta"), ('3', 'Muito Alta')], 'Prioridade', default='1')
    maintenance_type = fields.Selection(
        MAINTENANCE_TYPE_SELECTION, string='Tipo de Manutenção', required=True, default=None)
    # time_execution = fields.Float(
    #     "Tempo Execução", compute='_compute_time_execution', help="Tempo de execução em minutos", store=True)
    maintenance_duration = fields.Float(
        "Tempo Estimado", default='1.0', readonly=False)
    is_warranty = fields.Boolean(string="É garantia",  default=False)
    warranty_type = fields.Selection(
        string='Tipo de Garantia', selection=GARANTIA_SELECTION)
    date_request = fields.Datetime('Data Requisição', required=True, tracking=True)
    date_scheduled = fields.Datetime('Data Programada', required=True, tracking=True)
    #TODO
    # FAZER COM QUE A DATA DE EXECUÇÃO SEJA SEMPRE A DO RELATORIO DE ATENDIMENTO MAIS RECENTE
    date_execution = fields.Datetime('Data de Execução', tracking=True)
    #TODO
    # FAZER COM QUE A DATA DE INICIO DA EXECUÇÃO SEJA A DATAHORA DE INICIO DO PRIMEIRO RELATORIO
    date_start = fields.Datetime('Início da Execução',  tracking=True)
    #TODO
    # FAZER COM QUE A DATA DE INICIO DA EXECUÇÃO SEJA A DATAHORA DE FINAL DO ULTIMO RELATORIO
    date_finish = fields.Datetime('Término da Execução', tracking=True)
          
    # request_id = fields.Many2one(
    #     'engc.os.request', 'Solicitação Ref.',
    #     index=True, ondelete='restrict')
    problem_description = fields.Text('Descrição do chamado')

    
    solicitante = fields.Char(
        "Solicitante", size=60,
        help="Pessoa que solicitou a ordem de serviço",
        required=True,
    )   
  
    tecnico_id = fields.Many2one(
        'hr.employee', string='Técnico',  tracking=True,
    )

    empresa_manutencao = fields.Many2one(
        'res.partner',
        string='Empresa',
        tracking=True
        )

    repaired = fields.Boolean(u'Concluído', copy=False, readonly=True)

    equipment_id = fields.Many2one(
        'engc.equipment', 'Equipamento',
        index=True, required=True,
        company_dependent=True,
        help='Escolha o equipamento referente a Ordem de Servico.'
    )

    equipment_category = fields.Char(
        'Categoria',
        related='equipment_id.category_id.name',
        readonly=True,
        store=True
    )
    equipment_apelido = fields.Char(
        'Apelido',
        related='equipment_id.apelido',
        readonly=True,
        store=True
    )
    equipment_serial_number = fields.Char(
        'Número de Série',
        related='equipment_id.serial_number',
        readonly=True
    )
    equipment_model = fields.Char(
        'Modelo',
        related='equipment_id.model',
        readonly=True
    )
    # equipment_location = fields.Many2one(
    #	'Localizacao do equipamento',
    #	related='equipment_id.location_id',
    #	readonly=True
    # )
    equipment_tag = fields.Char(
        'Tag',
        related='equipment_id.tag',
        readonly=True
    )
    equipment_patrimonio = fields.Char(
        'Patrimonio do Equipamento',
        related='equipment_id.patrimony',
        readonly=True
    )
  
    service_description = fields.Text(
        "Descrição do Serviço", help="Descrição do serviço realizado ou a ser relalizado", 
        tracking=True
        )
  
    check_list_created = fields.Boolean(
        'Check List Created', tracking=True, default=False)
  
    relatorios_id = fields.One2many(
        string="Relatórios",
        comodel_name="engc.os.relatorios",
        inverse_name="os_id",        
        help="Relatórios de atendimento",
        check_company=True
    )
    relatorios_count = fields.Integer(compute='compute_relatorios_count')

    def compute_relatorios_count(self):
        for record in self:
            record.relatorios_count = self.env['engc.os.relatorios'].search_count(
                [('os_id', '=', self.id)])
    
    check_list_id = fields.One2many(
        string="Check-list",
        comodel_name='engc.os.verify.checklist',
        inverse_name="os_id",        
        help="Check List de instruções",
        check_company=True
    )
    check_list_count = fields.Integer(compute='compute_check_list_count')

    def compute_check_list_count(self):
        for record in self:
            record.check_list_count = self.env['engc.os.verify.checklist'].search_count(
                [('os_id', '=', self.id)])

    calibration_created = fields.Boolean("Calibração criada")
    calibration_id = fields.Many2one(
        string="Calibração Cod.",
        comodel_name="engc.calibration",
        help="Calibração gerada pela OS.",
        check_company=True
    )

    request_parts = fields.One2many(comodel_name='engc.os.request.parts',inverse_name="os_id",check_company=True)
    request_parts_count = fields.Integer(compute='compute_request_parts_count')

    def compute_request_parts_count(self):
        for record in self:
            record.request_parts_count = self.env['engc.os.request.parts'].search_count(
                [('os_id', '=', self.id)])

    @api.depends('relatorios')
    def _compute_time_execution(self):
        if self.relatorios:
            tempo = 0.0
            for rel in self.relatorios:
                tempo += rel.time_execution
            self.update({'time_execution': tempo})

    #******************************************
    #  ONCHANGES
    #
    #******************************************

    @api.onchange('date_scheduled')
    def onchange_scheduled_date(self):
        self.date_execution = self.date_scheduled

    @api.onchange('date_execution')
    def onchange_execution_date(self):
        if self.state == 'draft':
            self.date_scheduled = self.date_execution
        else:
            self.date_scheduled = self.date_execution

   
    @api.onchange('tecnicos_id')
    def onchange_tecnicos_id(self):
        _logger.debug(self.tecnicos_id)
        list_tecnicos_name = []
        for tecnico in self.tecnicos_id:
            list_tecnicos_name.append(tecnico.name)
        str_tecnicos = ", "
        str_tecnicos = str_tecnicos.join(list_tecnicos_name)
        body = "Modificado Tecnicos -> " + str_tecnicos
        # self.message_post(body=body)

    def verify_execution_rules(self):
        """ Verifica as regras para início da execução da OS
        
        """
        if self.filtered(lambda engc_os: engc_os.state == 'done'):
            raise UserError(_("O.S já concluída."))
        if self.filtered(lambda engc_os: engc_os.state == 'under_repair'):
            raise UserError(_('O.S. já em execução.'))
        return

  
    #******************************************
    #  ACTIONS
    #
    #******************************************
    
    def action_go_check_list(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Check-list'),
            'view_mode': 'tree,form',
            'res_model': 'engc.os.verify.checklist',
            'domain': [('os_id', '=', self.id)],
            'target': 'new',
            'context': {
                'default_os_id': self.id,
                'search_default_group_section': 1,
                'search_default_os_id': self.id,
                'expand': True,
                'create': True,
                'delete': True,
                
                
            },
        }
    def action_go_relatorios(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Relatorios'),
            'view_mode': 'tree,form',
            'res_model': 'engc.os.relatorios',
            'domain': [('os_id', '=', self.id)],
            'context': {
                'default_os_id': self.id,
                'create': False if self._verify_relatorio_aberto() else True
            },
        }
    
    def action_go_request_parts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Peças'),
            'view_mode': 'tree',
            'res_model': 'engc.os.request.parts',
            'domain': [('os_id', '=', self.id)],
            'context': "{'create': False,'delete': False,'edit':False}"
        }
    def action_make_check_list(self):
        self.create_checklist()
    
    def action_make_calibration(self):
        _logger.info("chamando calibracao")

        return {
            'name': _('Calibração'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'engc.calibration',
            'target': 'new',
            'context': {
                'default_os_id': self.id,
                'default_client_id': self.client_id.id,
                'default_equipment_id': self.equipment_id.id,
                'default_technician_id': self.tecnico_id.id
                         },
        }
        
        

    def action_draft(self):
        return self.action_repair_cancel_draft()
    
    

    
    def action_repair_cancel_draft(self):
        if self.filtered(lambda engc_os: engc_os.state != 'cancel'):
            raise UserError(
                _("Repair must be canceled in order to reset it to draft."))
        self.mapped('pecas').write({'state': 'draft'})
        return self.write({'state': 'draft'})

    
    def action_repair_pause(self):
        if self.filtered(lambda engc_os: engc_os.state != 'under_repair'):
            raise UserError(
                _("Repair must be canceled in order to reset it to draft."))

        return self.write({'state': 'pause_repair'})

    def relatorio_service_start(self, type_report):
        tecnicos_id = self.tecnicos_id
        motivo_chamado = ''
        servicos_executados = ''
        tem_pendencias = False
        pendencias=''

        if type_report == 'quotation':
            motivo_chamado = 'Realizar Orçamento'
            servicos_executados = 'Orçamento'
            tem_pendencias = True
            pendencias = 'Aprovação do orçamento'

        else:
            if self.maintenance_type == 'preventive':
                motivo_chamado = 'Realizar manutenção preventiva'
                servicos_executados = 'Realizado Check-list de manutenção Preventiva'
            if self.maintenance_type == 'instalacao':
                motivo_chamado = 'Realizar Instalação'
                servicos_executados = 'Realizado procedimentos e Check-list de instalação'
            if self.maintenance_type == 'treinamento':
                motivo_chamado = 'Realizar treinamento'
                servicos_executados = 'Realizado treinamento operacional'
            if self.maintenance_type == 'calibration':
                motivo_chamado = 'Realizar Calibração'
                servicos_executados = 'Realizado calibração conforme procedimentos padrão'
            if self.maintenance_type == 'corrective':
                motivo_chamado = self.description
                servicos_executados = ''
        self.env['engc.os.relatorio.servico'].create({
            'os_id': self.id,
            'type_report': type_report,
            'cliente_id': self.cliente_id.id,
            'equipment_id': self.equipment_id.id,
            'tecnicos_id': tecnicos_id,
            'motivo_chamado': motivo_chamado,
            'servico_executados': servicos_executados,
            'tem_pendencias': tem_pendencias,
            'pendencias': pendencias,
            'maintenance_duration': 1

        })

    def _verify_relatorio_aberto(self):
        self.ensure_one()
        domain = [('os_id','=', self.id), ('state','not in',['done','cancel'])]
        relatorios_count = self.env['engc.os.relatorios'].search_count(domain)
        return relatorios_count
    
   
    def verify_others_os_open(self):
        domain = ['&',
            ('maintenance_type', '=', 'corrective'),
            ('equipment_id', '=', self.equipment_id.id),
            ('state', '!=', 'draft'),
            ('state', '!=', 'cancel'),
            ('state', '!=', 'done'),
            ('state', '!=', 'reproved'),
            ('state', '!=', 'wait_authorization'),
            ('state', '!=', 'wait_parts'),
            ('id', '!=', self.id),
        ]
        result = self.env['engc.os'].search(domain)
        _logger.debug("Verificando outras OSES")
        _logger.debug(result)
        message_oses = 'Não é possível executar ação. Já existe(m) OS(s) para manutenção corretiva aberta desse equipamento:\n '
        
        for res in result:
            message_oses += res.name + '\n'
        
        if len(result) > 0:
            raise UserError(message_oses)

    
    def action_repair_aprove(self):
        self.message_post(body='Aprovado orçamento da ordem de serviço!')
        if self.state != 'done':
            res = self.write({'state': 'execution_ready'})
        return res
    
    
    def action_repair_reprove(self):
        self.message_post(body='Reprovado o orçamento da ordem de serviço!')
        if self.state != 'reproved':
            res = self.write({'state': 'reproved'})
        return res
    
    def action_wait_parts(self):
        self.message_post(body='Esperando peças chegar no estoque!')
        res = self.write({'state': 'wait_parts'})
        return res

    
    def action_start_execution(self):

        #self.verify_execution_rules()
        #self.repair_relatorio_service_start()
        

        _logger.info("Iniciando Execução")
        report_type = self.env.context.get('report_type')
        
        current_datetime = fields.Datetime.now()
        
        self.write({
             'state':'under_budget' if report_type == 'orcamento' else 'under_repair',
             'date_start': current_datetime.utcnow(),
             
        })
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        if employee.id:
            tecnico = employee
        else:
            tecnico = self.tecnico_id
        return {
            'name': _('Iniciar Execução'),
            'type': 'ir.actions.act_window',
            'target':'current',
            'view_mode': 'form',
            'res_model': 'engc.os.relatorios',
           # 'domain': [('curso_matricula_id', '=', self.curso_matricula_id.id)],
            'context': {
                'default_os_id': self.id,
                'default_technicians': [(4,[tecnico.id])],
                'default_data_atendimento':current_datetime,
                'default_report_type': report_type or None,
     
            }
        }
        

    
    def action_pause_repair_executar(self):

        self.verify_execution_rules()
        self.create_checklist()
        self.message_post(body='Pausada execução da ordem de serviço!')
        res = self.write(
            {'state': 'under_repair', 'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
        return res

    
    def action_repair_cancel(self):
        self.mapped('pecas').write({'state': 'cancel'})
        return self.write({'state': 'cancel'})

    
    def action_repair_end(self):
        """Finaliza execução da ordem de serviço.

        @return: True
        """

        if self.filtered(lambda engc_os: engc_os.state != 'under_repair'):
            raise UserError(
                _("A ordem de serviço de estar \"em execução\" para finalizar a execução."))

        if self.filtered(lambda engc_os: engc_os.state == 'done'):
            raise UserError(_('Ordem já finalizada'))

        if not self.relatorios_id:
            raise UserError(
                _("Para finalizar O.S. deve-se incluir pelo menos um relatório de serviço."))
            return False
        if self.relatorios_id.filtered(lambda x: x.state == 'draft'):
            raise UserError(
                _("Para finalizar O.S. deve-se concluir todos os relatorios de serviço."))
            return False
           

        # verificando se pecas foram aplicadas
        for p in self.request_parts:
            if not p.state in ['aplicada','cancel','nao_autorizada']:
                raise UserError(
                    _("Para finalizar O.S. todas as peças devem ser aplicadas"))
                return False
        # if self.check_list_created:
        # for check in self.check_list:
        #     if not check.check:
        #         raise UserError(
        #             _("Para finalizar O.S. todas as instruções do check-list devem estar concluídas"))
        #         return False

        vals = {
            'state': 'done',
            'date_execution': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        # self.action_repair_done()
        res = self.write(vals)
        # if res:
        #     if self.request_id.id:
        #         self.request_id.action_finish_request()
        #         _logger.debug("Concluída Solicitação")
        #     else:
        #         _logger.debug("Não existe solicitação para OS. Continuando...")
        #     _logger.debug("Finalizando relatorios.")
        #     self.finish_report()
        #     return True
        # else:
        #     _logger.debug("Erro ao atualizar OS.")
        #     return False

    def repair_relatorio_service_start(self):
        date_now = datetime.now()
        type_report = 'repair'
        self.relatorio_service_start(type_report)
                                   
      
    def finish_report(self):
        _logger.debug("Procurando relatorios...")
        if self.relatorios:
            for rec in self.relatorios:
                rec.state = 'done'
        return True

    # utilizado na venda para atorizar Ordem de serviço
    
    def approve(self):
        _logger.debug("Mudando state da os %s", self.name)
        for item in self:
            if item.state != 'done':
                item.write({'state': 'execution_ready'})
                post_vars = {'subject': "Ordem Aprovada",
                            'body': "A cotação foi aprovada pelo cliente, favor agendar execução",
                           } # Where "4" adds the ID to the list 
                                       # of followers and "3" is the partner ID 
                
                item.message_post(body="A cotação foi aprovada pelo cliente, favor agendar execução",subject="Ordem Aprovada",partner_ids=[3])
        _logger.debug("os state=%s ", self.state)


    def add_service(self):
        """
            Adiciona serviço de acordo com a OS
            Verifica se equipamento em garantia, serviço em contrato e coloca o serviço adequado
        """
        _logger.debug("adicionando serviço...")
        _logger.debug(self.contrato) 
        _logger.debug("procurando serviço já adicionados na OS")

        added_services = self.env['engc.os.servicos.line'].search([('os_id', '=',self.id )], offset=0, limit=None, order=None, count=False)
        servicos_line = []

        _logger.debug("Serviços achados para OS")
        for serv_line in added_services: 
            servicos_line.append(serv_line.product_id)
            _logger.debug(serv_line.product_id.name)
        
          
        _logger.debug("Serviços Padrão")
        service_default = self.env['product.product'].search([('name','ilike','Manutenção Geral')], limit=1)
        _logger.debug(service_default.name)
    
        if not service_default.id:
            raise UserError(_("Serviço padrão não configurado. Favor configurá-lo. Adicione o serviço 'Manutenção Geral'"))
        product_id = service_default
        
            
        if self.contrato.id:
            _logger.debug("Mudando serviço pois existe contrato para esse equipamento:")
            _logger.debug("Colocando serviço padrão para contrato:")
            if self.contrato.service_product_id.id:
                #verificando se tem esse serviço ja foi adicionado
                if self.contrato.service_product_id in servicos_line:
                    _logger.debug("Já existe serviço adicionado: %s", self.contrato.service_product_id.name)
                else:
                    _logger.debug("Serviço adicionado: %s", self.contrato.service_product_id.name)
                    product_id = self.contrato.service_product_id
        if self.is_warranty:
            if self.warranty_type == "fabrica":
                _logger.debug("Serviço em garantia fabrica")
                service_warranty = self.env['product.product'].search([('name','ilike','Serviço em garantia de fábrica')], limit=1)
                if not service_warranty.id:
                    raise UserError(_("Serviço garantia não configurado. Favor configurá-lo. Adicione o serviço 'Serviço em garantia de fábrica'"))
                
            else:
                _logger.debug("Serviço em garantia própria")
                service_warranty = self.env['product.product'].search([('name','ilike','Serviço em garantia')], limit=1)
                if not service_warranty.id:
                    raise UserError(_("Serviço garantia não configurado. Favor configurá-lo. Adicione o serviço 'Serviço em garantia'"))

            product_id= service_warranty
            
        _logger.debug("Verificando tempo para adicionar no serviço")
        if self.time_execution > 0:
            _logger.debug("Colocado tempo de execução no serviço: %s",self.time_execution )
            product_uom_qty = self.time_execution
            
        else:
            _logger.debug("Colocado tempo estimado no serviço: %s", self.maintenance_duration)
            product_uom_qty = self.maintenance_duration
        _logger.debug("Create servicos line:")

        if self.description:
            name = self.description
        else:
            name = product_id.display_name

        if len(servicos_line) == 0:
            _logger.debug("Serviços sera adicionado")
            self.servicos = [(0,0,{
                    'os_id' : self.id,
                    'automatic': True,
                    'name': name,
                    'product_id' : product_id.id,
                    'product_uom': product_id.uom_id.id,
                    'product_uom_qty' : product_uom_qty
                })]
            _logger.debug( self.servicos)
        else: 
            _logger.debug("Serviços sera apenas atualizado")
            for servico in added_services:
             
                if servico.automatic:
                    _logger.debug("Encontrado servicos adicionados automaticamente, atualizando")
                    self.servicos = [(1,servico.id,{
                            'os_id' : self.id,
                            'automatic': True,
                            'name': name,
                            'product_id' : product_id.id,
                            'product_uom': product_id.uom_id.id,
                            'product_uom_qty' : product_uom_qty
                        })]

        return self.servicos

    def create_checklist(self):
        """Cria a lista de verificacao caso a os seja preventiva."""
        if self.maintenance_type == 'preventive' or self.maintenance_type == 'loan' or self.maintenance_type == 'calibration':
            _logger.debug("Criando Checklist")
            if not self.equipment_id:
                raise ValidationError(_("Não está definido o campo equipamento na OS"))
            
            maintenance_plan = self.equipment_id.get_maintenance_plan()
            if not maintenance_plan:
                raise ValidationError(_("Não há plano de manutenção configurado no equipamento ou na sua categoria"))
            instructions = maintenance_plan.instrucion_ids

           
            os_check_list = self.env['engc.os.verify.checklist'].search(
                [('os_id', '=', self.id)])
            if os_check_list:
                raise ValidationError(_("Check list já criado. Exclua toda check-list para gerar novamente"))

            for i in instructions:
                instructions = os_check_list.create(
                    {'os_id': self.id, 'instruction': i.name})
                _logger.debug(i)

            #self.check_list_created = True