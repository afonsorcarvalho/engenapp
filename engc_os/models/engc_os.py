from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class EngcOs(models.Model):
    _name = 'engc.os'
    _description = 'Ordem de Serviço'
    _inherit = ['mail.thread', 'mail.activity.mixin']
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

    # Constantes para seleção de tipos de manutenção
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
        """
        Cria novas ordens de serviço e gera automaticamente o número da sequência.
        
        Args:
            vals_list: Lista de dicionários com os valores para criar as OS.
            
        Returns:
            recordset: Registros criados.
        """
        for vals in vals_list:
            if 'name' not in vals or vals.get('name') == _('New'):
                company_id = vals.get('company_id')
                if company_id:
                    vals['name'] = self.env['ir.sequence'].with_company(company_id).next_by_code(
                        'engc.os_sequence') or _('New')
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code('engc.os_sequence') or _('New')
        return super(EngcOs, self).create(vals_list)

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
    request_service_id = fields.Many2one('engc.request.service')
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
    
    periodicity_ids = fields.Many2many(
        string='Periodicidade',comodel_name='engc.maintenance_plan.periodicity'
    )
    department = fields.Many2one('hr.department', string="Departamento", check_company=True)
    maintenance_duration = fields.Float(
        "Tempo Estimado", default='1.0', readonly=False)
    is_warranty = fields.Boolean(string="É garantia",  default=False)
    warranty_type = fields.Selection(
        string='Tipo de Garantia', selection=GARANTIA_SELECTION)
    date_request = fields.Datetime('Data Requisição', required=True, tracking=True)
    date_scheduled = fields.Datetime('Data Programada', required=True, tracking=True)
    date_execution = fields.Datetime('Data de Execução', compute="_compute_date_execution", tracking=True)
    date_start = fields.Datetime('Início da Execução',  compute="_compute_date_start",tracking=True)
       
    @api.depends('relatorios_id', 'relatorios_id.data_atendimento', 'relatorios_id.state')
    def _compute_date_start(self):
        """
        Calcula o início da execução com base no início de atendimento 
        do relatório de serviço mais antigo (exclui cancelados).
        """
        for record in self:
            relatorios_ativos = record.relatorios_id.filtered(lambda r: r.state != 'cancel')
            relatorios_com_data = relatorios_ativos.filtered('data_atendimento')
            record.date_start = min(relatorios_com_data.mapped("data_atendimento")) if relatorios_com_data else False
    
    @api.depends('relatorios_id', 'relatorios_id.data_fim_atendimento', 'relatorios_id.state')
    def _compute_date_execution(self):
        """
        Calcula a data de execução com base no fim do atendimento 
        do relatório de serviço mais recente (exclui cancelados).
        """
        for record in self:
            relatorios_ativos = record.relatorios_id.filtered(lambda r: r.state != 'cancel')
            relatorios_com_data = relatorios_ativos.filtered('data_fim_atendimento')
            record.date_execution = max(relatorios_com_data.mapped("data_fim_atendimento")) if relatorios_com_data else False
                


           

    date_finish = fields.Datetime('Término da Execução', compute="_compute_date_finish", tracking=True)
    
    @api.depends('relatorios_id', 'relatorios_id.data_fim_atendimento', 'relatorios_id.state')
    def _compute_date_finish(self):
        """
        Calcula o término da execução com base no fim do atendimento 
        do relatório de serviço mais recente (exclui cancelados).
        Nota: Atualmente usa a mesma lógica de _compute_date_execution.
        """
        for record in self:
            relatorios_ativos = record.relatorios_id.filtered(lambda r: r.state != 'cancel')
            relatorios_com_data = relatorios_ativos.filtered('data_fim_atendimento')
            record.date_finish = max(relatorios_com_data.mapped("data_fim_atendimento")) if relatorios_com_data else False
    
    # ==========================================
    #  VALIDAÇÕES (CONSTRAINTS)
    # ==========================================
    
    @api.constrains('date_request', 'date_scheduled')
    def _check_date_request_vs_scheduled(self):
        """
        Valida que a Data Requisição não pode ser maior que a Data Programada.
        
        Raises:
            ValidationError: Se a data de requisição for posterior à data programada.
        """
        for record in self:
            if record.date_request and record.date_scheduled and record.date_request > record.date_scheduled:
                raise ValidationError(
                    _('A Data Requisição não pode ser maior que a Data Programada.\n'
                      'Data Requisição: %s\n'
                      'Data Programada: %s') % (
                        record.date_request.strftime('%d/%m/%Y %H:%M:%S'),
                        record.date_scheduled.strftime('%d/%m/%Y %H:%M:%S')
                    )
                )
    
    @api.constrains('date_request', 'date_start')
    def _check_date_request_vs_start(self):
        """
        Valida que a Data Requisição não pode ser maior que o Início da Execução.
        
        Raises:
            ValidationError: Se a data de requisição for posterior ao início da execução.
        """
        for record in self:
            if record.date_request and record.date_start and record.date_request > record.date_start:
                raise ValidationError(
                    _('A Data Requisição não pode ser maior que o Início da Execução.\n'
                      'Data Requisição: %s\n'
                      'Início da Execução: %s') % (
                        record.date_request.strftime('%d/%m/%Y %H:%M:%S'),
                        record.date_start.strftime('%d/%m/%Y %H:%M:%S')
                    )
                )
    
    @api.constrains('date_start', 'date_finish')
    def _check_date_start_vs_finish(self):
        """
        Valida que o Início da Execução deve ser anterior ao Término da Execução.
        
        Raises:
            ValidationError: Se o início da execução for igual ou posterior ao término.
        """
        for record in self:
            if record.date_start and record.date_finish and record.date_start >= record.date_finish:
                raise ValidationError(
                    _('O Início da Execução deve ser anterior ao Término da Execução.\n'
                      'Início da Execução: %s\n'
                      'Término da Execução: %s') % (
                        record.date_start.strftime('%d/%m/%Y %H:%M:%S'),
                        record.date_finish.strftime('%d/%m/%Y %H:%M:%S')
                    )
                )
    
    @api.constrains('maintenance_type', 'periodicity_ids')
    def _check_periodicity_required_for_preventive(self):
        """
        Valida que a Periodicidade é obrigatória quando o tipo de manutenção é Preventiva.
        
        Raises:
            ValidationError: Se a manutenção for preventiva e não houver periodicidade definida.
        """
        for record in self:
            if record.maintenance_type == 'preventive' and not record.periodicity_ids:
                raise ValidationError(
                    _('⚠️ A Periodicidade é obrigatória para manutenção preventiva.')
                )
    
    @api.onchange('maintenance_type')
    def _onchange_maintenance_type(self):
        """
        Preenche automaticamente a descrição do chamado quando o tipo de manutenção é Preventiva.
        """
        if self.maintenance_type == 'preventive':
            self.problem_description = 'Manutenção preventiva conforme check-list'
          
    request_id = fields.Many2one(
         'engc.request.service', 'Solicitação Ref.',
         index=True, ondelete='restrict')
    problem_description = fields.Text('Descrição do chamado')

    
    solicitante = fields.Char(
        "Solicitante", size=60,
        help="Pessoa que solicitou a ordem de serviço",
        required=True,
    )   
  
    tecnico_id = fields.Many2one(
        'hr.employee', string='Técnico',  tracking=True,
    )
    #TODO para serviços com mais de um tecnico auxiliando, ainda tem que passar para o relatorio esses técnicos
    tecnico_aux_id = fields.Many2one(
        'hr.employee', string='Técnico Aux ',  tracking=True,
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
    relatorios_count = fields.Integer(compute='_compute_relatorios_count')
    relatorios_pending_count = fields.Integer(compute='_compute_relatorios_pending_done')
    relatorios_done_count = fields.Integer(compute='_compute_relatorios_pending_done')

    @api.depends('relatorios_id', 'relatorios_id.state')
    def _compute_relatorios_count(self):
        """Calcula a quantidade de relatórios associados à OS (exclui cancelados)."""
        for record in self:
            record.relatorios_count = len(
                record.relatorios_id.filtered(lambda r: r.state != 'cancel')
            )

    @api.depends('relatorios_id', 'relatorios_id.state')
    def _compute_relatorios_pending_done(self):
        """Quantidade de relatórios não concluídos (vermelho) e concluídos (verde).
        Relatórios cancelados não são contabilizados em nenhuma das bolinhas."""
        for record in self:
            relatorios_ativos = record.relatorios_id.filtered(lambda r: r.state != 'cancel')
            record.relatorios_pending_count = len(
                relatorios_ativos.filtered(lambda r: r.state != 'done')
            )
            record.relatorios_done_count = len(
                relatorios_ativos.filtered(lambda r: r.state == 'done')
            )

    relatorios_time_execution = fields.Float(compute="_compute_relatorios_time_execution")

    @api.depends('relatorios_id', 'relatorios_id.time_execution', 'relatorios_id.state')
    def _compute_relatorios_time_execution(self):
        """Calcula o tempo total de execução de todos os relatórios (exclui cancelados)."""
        for record in self:
            relatorios_ativos = record.relatorios_id.filtered(lambda r: r.state != 'cancel')
            record.relatorios_time_execution = sum(relatorios_ativos.mapped("time_execution"))
            
    
    check_list_id = fields.One2many(
        string="Check-list",
        comodel_name='engc.os.verify.checklist',
        inverse_name="os_id",        
        help="Check List de instruções",
        check_company=True
    )
    check_list_count = fields.Integer(compute='_compute_check_list_count')
    check_list_pending_count = fields.Integer(compute='_compute_check_list_pending_done')
    check_list_done_count = fields.Integer(compute='_compute_check_list_pending_done')

    @api.depends('check_list_id')
    def _compute_check_list_count(self):
        """Calcula a quantidade de itens do checklist associados à OS."""
        for record in self:
            record.check_list_count = len(record.check_list_id)

    @api.depends('check_list_id', 'check_list_id.check')
    def _compute_check_list_pending_done(self):
        """Quantidade de itens do checklist pendentes (vermelho) e concluídos (verde)."""
        for record in self:
            record.check_list_pending_count = len(record.check_list_id.filtered(lambda c: not c.check))
            record.check_list_done_count = len(record.check_list_id.filtered(lambda c: c.check))

    def get_checklist_grouped_by_section(self):
        """
        Retorna os itens do checklist agrupados por seção, ordenados por seção e sequence.
        Usado no template do relatório para exibir o checklist agrupado.
        """
        self.ensure_one()
        if not self.check_list_id:
            return []
        
        # Agrupa por seção preservando a ordem de aparição
        section_order = []
        by_section = {}
        for item in self.check_list_id.sorted('sequence'):
            sec = item.section
            sec_name = sec.name if sec else _("Sem Seção")
            sec_id = sec.id if sec else 0
            if sec_id not in by_section:
                by_section[sec_id] = {
                    'name': sec_name,
                    'items': []
                }
                section_order.append(sec_id)
            by_section[sec_id]['items'].append(item)
        
        # Retorna lista de dicionários com seção e itens
        result = []
        for sec_id in section_order:
            result.append(by_section[sec_id])
        return result

    calibration_created = fields.Boolean("Calibração criada")
    calibration_id = fields.Many2one(
        string="Calibração Cod.",
        comodel_name="engc.calibration",
        help="Calibração gerada pela OS.",
        check_company=True
    )

    request_parts = fields.One2many(comodel_name='engc.os.request.parts',inverse_name="os_id",check_company=True)
    request_parts_count = fields.Integer(compute='compute_request_parts_count')
    request_parts_requested_count = fields.Integer(compute='_compute_request_parts_requested_applied')
    request_parts_applied_count = fields.Integer(compute='_compute_request_parts_requested_applied')
    signature =  fields.Image('Signature', help='Signature', copy=False, attachment=True)
    signature2 =  fields.Image('Signature2', help='Signature', copy=False, attachment=True)
    technician_signature_date = fields.Datetime(
        string='Data da Assinatura do Técnico',
        readonly=True,
        help='Data em que o técnico assinou a ordem de serviço'
    )
    supervisor_signature_date = fields.Datetime(
        string='Data da Assinatura do Supervisor',
        readonly=True,
        help='Data em que o supervisor assinou a ordem de serviço'
    )

    @api.depends('request_parts')
    def compute_request_parts_count(self):
        """Calcula a quantidade de solicitações de peças associadas à OS."""
        for record in self:
            record.request_parts_count = len(record.request_parts)

    @api.depends('request_parts', 'request_parts.state')
    def _compute_request_parts_requested_applied(self):
        """Quantidade de peças requisitadas (vermelho) e aplicadas (verde)."""
        for record in self:
            record.request_parts_requested_count = len(
                record.request_parts.filtered(
                    lambda p: p.state in ('requisitada', 'autorizada')
                )
            )
            record.request_parts_applied_count = len(
                record.request_parts.filtered(lambda p: p.state == 'aplicada')
            )

    # ==========================================
    #  ONCHANGES
    # ==========================================

    @api.onchange('date_scheduled')
    def onchange_scheduled_date(self):
        """Atualiza a data de execução quando a data programada é alterada."""
        if self.date_scheduled:
            self.date_execution = self.date_scheduled

    @api.onchange('date_execution')
    def onchange_execution_date(self):
        """Atualiza a data programada quando a data de execução é alterada."""
        if self.date_execution:
            self.date_scheduled = self.date_execution

    @api.onchange('tecnico_id')
    def onchange_tecnico_id(self):
        self.signature = ""
        
        
   
  
      

    def verify_execution_rules(self):
        """
        Verifica as regras para início da execução da OS.
        
        Raises:
            UserError: Se a OS já estiver concluída ou em execução.
        """
        os_done = self.filtered(lambda os: os.state == 'done')
        if os_done:
            raise UserError(_("O.S já concluída."))
        
        os_in_repair = self.filtered(lambda os: os.state == 'under_repair')
        if os_in_repair:
            raise UserError(_('O.S. já em execução.'))
    
    def _check_checklist_preventive(self):
        """
        Valida o checklist para ordens de serviço de manutenção preventiva.
        
        Verifica se:
        - Existe um checklist criado
        - Todos os itens do checklist estão checkados
        
        Se todas as validações passarem, marca todos os itens como concluídos.
        
        Raises:
            UserError: Se não houver checklist ou se houver itens não checkados.
        """
        for record in self:
            if record.maintenance_type == 'preventive':
                if not record.check_list_id:
                    raise UserError(
                        _("⚠️ Para finalizar uma O.S. de manutenção preventiva, é necessário ter um check-list criado."))
                # Verifica se todos os itens do checklist estão checkados
                itens_nao_checkados = record.check_list_id.filtered(lambda cl: not cl.check)
                if itens_nao_checkados:
                    # Monta lista de itens não checkados agrupados por seção
                    itens_por_secao = {}
                    for item in itens_nao_checkados:
                        nome_item = item.instruction or _('Item sem descrição')
                        nome_secao = item.section.name if item.section else _('Sem seção')
                        if nome_secao not in itens_por_secao:
                            itens_por_secao[nome_secao] = []
                        itens_por_secao[nome_secao].append(nome_item)
                    
                    # Formata a mensagem agrupando por seção
                    lista_formatada = []
                    for secao, itens in itens_por_secao.items():
                        lista_formatada.append(_("📋 Seção: %s") % secao)
                        for item in itens:
                            lista_formatada.append('  ❌ %s' % item)
                    
                    raise UserError(
                        _("⚠️ Para finalizar uma O.S. de manutenção preventiva, todos os itens do check-list devem estar checkados.\n\n"
                          "Itens não checkados (%d):\n%s") % (
                            len(itens_nao_checkados),
                            '\n'.join(lista_formatada)
                        ))
                # Marca todos os itens do checklist como concluídos
                for cl in record.check_list_id:
                    cl.state = 'done'

  
    # ==========================================
    #  ACTIONS
    # ==========================================
    
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
        """
        Abre a lista de relatórios de atendimento da ordem de serviço.
        
        Returns:
            dict: Ação para abrir a lista de relatórios.
        """
        self.ensure_one()
        
        # Verifica se a OS está finalizada para desabilitar criação de novos relatórios
        can_create = False if (self.state == 'done' or self._verify_relatorio_aberto()) else True
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Relatorios'),
            'view_mode': 'tree,form',
            'res_model': 'engc.os.relatorios',
            'domain': [('os_id', '=', self.id)],
            'context': {
                'default_os_id': self.id,
                'default_data_atendimento': fields.Datetime.now(),
                'default_data_fim_atendimento': fields.Datetime.now() + timedelta(hours=1),
                'default_technicians': [(4, [self.tecnico_id.id])] if self.tecnico_id else [],
                'create': can_create
            },
        }
    
    def action_add_new_relatorio(self):
        """
        Abre um formulário para criar um novo relatório de atendimento.
        Este método é chamado pelo botão "Adicionar Novo Relatório" na view de OS.
        
        Returns:
            dict: Ação para abrir o formulário de criação de relatório
        """
        self.ensure_one()
        
        # Verifica se a OS está finalizada
        if self.state == 'done':
            raise UserError(
                _("⚠️ Não é possível adicionar relatórios em uma Ordem de Serviço finalizada."))
        
        # Prepara os valores padrão para o novo relatório
        current_datetime = fields.Datetime.now()
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        tecnico = self.tecnico_id if self.tecnico_id else employee
        
        # Prepara os técnicos
        technicians_vals = []
        if tecnico:
            technicians_vals = [(4, tecnico.id)]
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Adicionar Novo Relatório'),
            'view_mode': 'form',
            'res_model': 'engc.os.relatorios',
            'target': 'current',
            'context': {
                'default_os_id': self.id,
                'default_company_id': self.company_id.id if self.company_id else False,
                'default_data_atendimento': current_datetime,
                'default_data_fim_atendimento': current_datetime + timedelta(hours=1),
                'default_technicians': technicians_vals,
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
    
    def action_relatorio_atendimento_resumo(self):
        """
        Abre o wizard para gerar relatório resumido de atendimentos.
        
        Returns:
            dict: Action para abrir o wizard
        """
        return {
            'type': 'ir.actions.act_window',
            'name': _('Relatório Resumido de Atendimentos'),
            'res_model': 'wizard.relatorio.atendimento.resumo',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_company_id': self.env.company.id,
            },
        }

    #TODO gerar o check list e abri-lo   
    def action_make_check_list(self):

        #verificando se os é de preventiva
        if self.maintenance_type not in ['preventive']:
            raise ValidationError(_("Esta OS não é de Manutenção Preventiva"))
        
        # verficando se há periodicidade cadastrada
        if len(self.periodicity_ids) == 0:
            raise ValidationError(_("Você deve selecionar Periodicidade da Preventiva para gerar Check-list"))
        self.create_checklist()
        return self.action_go_check_list()

    #TODO VERIFICA SE ESSA FUNÇÃO ESTÁ FUNCIONANDO
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
        
  
    
    def action_repair_pause(self):
        """
        Pausa a execução da ordem de serviço.
        
        Raises:
            UserError: Se a OS não estiver em execução.
            
        Returns:
            bool: True se a operação foi bem-sucedida.
        """
        os_not_in_repair = self.filtered(lambda os: os.state != 'under_repair')
        if os_not_in_repair:
            raise UserError(
                _("A ordem de serviço deve estar em execução para ser pausada."))
        return self.write({'state': 'pause_repair'})

    # def relatorio_service_start(self, type_report):
    #     tecnicos_id = self.tecnicos_id
    #     motivo_chamado = ''
    #     servicos_executados = ''
    #     tem_pendencias = False
    #     pendencias=''

    #     if type_report == 'quotation':
    #         motivo_chamado = 'Realizar Orçamento'
    #         servicos_executados = 'Orçamento'
    #         tem_pendencias = True
    #         pendencias = 'Aprovação do orçamento'

    #     else:
    #         if self.maintenance_type == 'preventive':
    #             motivo_chamado = 'Realizar manutenção preventiva'
    #             servicos_executados = 'Realizado Check-list de manutenção Preventiva'
    #         if self.maintenance_type == 'instalacao':
    #             motivo_chamado = 'Realizar Instalação'
    #             servicos_executados = 'Realizado procedimentos e Check-list de instalação'
    #         if self.maintenance_type == 'treinamento':
    #             motivo_chamado = 'Realizar treinamento'
    #             servicos_executados = 'Realizado treinamento operacional'
    #         if self.maintenance_type == 'calibration':
    #             motivo_chamado = 'Realizar Calibração'
    #             servicos_executados = 'Realizado calibração conforme procedimentos padrão'
    #         if self.maintenance_type == 'corrective':
    #             motivo_chamado = self.description
    #             servicos_executados = ''
    #     self.env['engc.os.relatorio.servico'].create({
    #         'os_id': self.id,
    #         'type_report': type_report,
    #         'cliente_id': self.cliente_id.id,
    #         'equipment_id': self.equipment_id.id,
    #         'tecnicos_id': tecnicos_id,
    #         'motivo_chamado': motivo_chamado,
    #         'servico_executados': servicos_executados,
    #         'tem_pendencias': tem_pendencias,
    #         'pendencias': pendencias,
    #         'maintenance_duration': 1

    #     })
    def create_relatorio(self):
        """
        Cria um novo relatório de atendimento para a ordem de serviço.
        
        Raises:
            UserError: Se a OS estiver concluída.
            
        Returns:
            recordset: Relatório criado.
        """
        self.ensure_one()
        
        # Valida se a OS está concluída
        if self.state == 'done':
            raise UserError(
                _("⚠️ Não é possível criar relatórios em uma Ordem de Serviço concluída."))
        
        # Constante para duração padrão do atendimento (1 hora)
        DEFAULT_ATTENDANCE_DURATION_HOURS = 1
        
        report_type = self.env.context.get('report_type')
        current_datetime = fields.Datetime.now()
        
        # Busca o técnico: prioriza o técnico da OS, senão usa o funcionário logado
        employee = self.env['hr.employee'].search(
            [('user_id', '=', self.env.user.id)], limit=1
        )
        tecnico = self.tecnico_id or employee
        
        # Prepara descrição e resumo baseado no tipo de manutenção
        fault_description, service_summary = self._prepare_relatorio_descriptions()
        
        # Prepara os técnicos (campo obrigatório)
        technicians_vals = [(4, tecnico.id)] if tecnico else []

        return self.env['engc.os.relatorios'].create({
            'os_id': self.id,
            'report_type': report_type,
            'data_atendimento': current_datetime,
            'data_fim_atendimento': current_datetime + timedelta(hours=DEFAULT_ATTENDANCE_DURATION_HOURS),
            'technicians': technicians_vals,
            'fault_description': fault_description,
            'service_summary': service_summary,
        })
    
    def _prepare_relatorio_descriptions(self):
        """
        Prepara a descrição do defeito e o resumo do serviço baseado no tipo de manutenção.
        
        Returns:
            tuple: (fault_description, service_summary)
        """
        fault_description = ""
        service_summary = ""
        
        if self.maintenance_type == 'preventive':
            fault_description = "Manutenção Preventiva"
            
            # Monta o resumo com as periodicidades selecionadas
            if self.periodicity_ids:
                periodicity_names = self.periodicity_ids.mapped('name')
                periodicity_str = ', '.join(periodicity_names)
                service_summary = (
                    f"Realizada a Preventiva ({periodicity_str}) "
                    f"seguindo o check-list de preventiva do equipamento."
                )
            else:
                service_summary = (
                    "Realizada a Preventiva seguindo o check-list de preventiva do equipamento."
                )
        
        return fault_description, service_summary
    

    def _verify_relatorio_aberto(self):
        """
        Verifica se existe algum relatório aberto (não concluído e não cancelado).
        
        Returns:
            int: Quantidade de relatórios abertos.
        """
        self.ensure_one()
        relatorios_abertos = self.relatorios_id.filtered(
            lambda r: r.state not in ['done', 'cancel']
        )
        return len(relatorios_abertos)
    
   
    def verify_others_os_open(self):
        """
        Verifica se existem outras OS de manutenção corretiva abertas para o mesmo equipamento.
        
        Raises:
            UserError: Se existirem outras OS corretivas abertas para o equipamento.
        """
        estados_finais = ['draft', 'cancel', 'done', 'reproved', 'wait_authorization', 'wait_parts']
        
        domain = [
            ('maintenance_type', '=', 'corrective'),
            ('equipment_id', '=', self.equipment_id.id),
            ('state', 'not in', estados_finais),
            ('id', '!=', self.id),
        ]
        
        outras_os_abertas = self.env['engc.os'].search(domain)
        
        if outras_os_abertas:
            _logger.debug("Encontradas outras OS corretivas abertas: %s", outras_os_abertas.mapped('name'))
            os_lista = '\n'.join([f"- {os.name}" for os in outras_os_abertas])
            raise UserError(
                _('Não é possível executar ação. Já existe(m) OS(s) para manutenção corretiva '
                  'aberta desse equipamento:\n%s') % os_lista
            )

    
    def action_repair_aprove(self):
        self.message_post(body='Aprovado orçamento da ordem de serviço!')
        if self.state != 'done':
            return self.write({'state': 'execution_ready'})
       
    
    
    def action_repair_reprove(self):
        self.message_post(body='Reprovado o orçamento da ordem de serviço!')
        if self.state != 'reproved':
            return self.write({'state': 'reproved'})
        
    
    def action_wait_parts(self):
        self.message_post(body='Esperando peças chegar no estoque!')
        return self.write({'state': 'wait_parts'})
        

    
    def action_start_execution(self):

        #self.verify_execution_rules()
        #self.repair_relatorio_service_start()


        _logger.info("Iniciando Execução")
        current_datetime = fields.Datetime.now()
        report_type = self.env.context.get('report_type')

        # Se for manutenção preventiva, gera o checklist primeiro (se ainda não existir), sem abrir a tela do checklist
        if self.maintenance_type == 'preventive' and not self.check_list_id:
            self.create_checklist()

        # Para todos os tipos de manutenção, cria o relatório
        id_relatorio = self.create_relatorio()
        if not id_relatorio:
            raise UserError("Erro ao gerar relatório")

        # Se for preventiva e há checklist na OS, adiciona todas as instruções do checklist ao relatório
        if self.maintenance_type == 'preventive' and self.check_list_id:
            id_relatorio.write({
                'checklist_item_ids': [(6, 0, self.check_list_id.ids)],
            })

        self.write({
             'state':'under_budget' if report_type == 'orcamento' else 'under_repair',
             'date_start': current_datetime,

        })


        return {
            'res_id': id_relatorio.id,
            'name': _('Iniciar Execução'),
            'type': 'ir.actions.act_window',
            'target':'current',
            'view_mode': 'form',
            'res_model': 'engc.os.relatorios',

        }
        
        

    
    def action_pause_repair_executar(self):
        """
        Retoma a execução da ordem de serviço após pausa.
        
        Raises:
            UserError: Se as regras de execução não forem atendidas.
            
        Returns:
            bool: True se a operação foi bem-sucedida.
        """
        self.verify_execution_rules()
        self.create_checklist()
        self.message_post(body='Retomada execução da ordem de serviço!')
        return self.write({
            'state': 'under_repair',
            'date_start': fields.Datetime.now()
        })

    
    # def action_repair_cancel(self):
    #     self.mapped('pecas').write({'state': 'cancel'})
    #     return self.write({'state': 'cancel'})

    
    def _get_relatorios_nao_concluidos(self):
        """
        Retorna os relatórios de atendimento que ainda não foram concluídos.
        
        Returns:
            recordset: Relatórios com estado 'draft' (não concluídos)
        """
        self.ensure_one()
        return self.relatorios_id.filtered(lambda r: r.state == 'draft')
    
    def _get_pecas_nao_aplicadas(self):
        """
        Retorna as peças que ainda não foram aplicadas, canceladas ou não autorizadas.
        
        Returns:
            recordset: Peças que não estão em estados finais válidos.
        """
        self.ensure_one()
        estados_validos = ['aplicada', 'cancel', 'nao_autorizada']
        return self.request_parts.filtered(lambda p: p.state not in estados_validos)
    
    def action_repair_end(self):
        """Finaliza execução da ordem de serviço.
        
        Verifica se há assinatura antes de concluir e gera/anexa o PDF da OS concluída.

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
          
        relatorios_nao_concluidos = self._get_relatorios_nao_concluidos()
        if relatorios_nao_concluidos:
            relatorios_lista = '\n'.join([f"- {r.name}" for r in relatorios_nao_concluidos])
            raise UserError(
                _("⚠️ Para finalizar O.S. deve-se concluir todos os relatórios de serviço.\n\n"
                  "Relatórios não concluídos:\n%s") % relatorios_lista)
                
        # Verifica se todas as peças foram aplicadas, canceladas ou não autorizadas
        pecas_nao_aplicadas = self._get_pecas_nao_aplicadas()
        if pecas_nao_aplicadas:
            raise UserError(
                _("Para finalizar O.S. todas as peças devem ser aplicadas. "
                  "Crie um novo relatório para aplicação da peça ou cancelamento da peça."))
        
        # verificando se todos check-list foram realizados (apenas para manutenção preventiva)
        self._check_checklist_preventive()
        
        # Verifica se há assinatura antes de permitir concluir
        # Recarrega os registros do banco para garantir que temos os dados mais recentes
        self.invalidate_recordset(['signature'])
        for record in self:
            # Verifica se há assinatura salva no banco de dados
            if not record.signature:
                raise UserError(
                    _("⚠️ Para finalizar a O.S., é obrigatório assinar o documento.\n\n"
                      "Por favor, assine o documento e salve o formulário antes de concluir a ordem de serviço."))
              
       

        vals = {
            'state': 'done',
            'date_execution': fields.Datetime.now(),
        }
     
        res = self.write(vals)
        if res:
            # Verifica se há solicitação de serviço associada e finaliza
            # Nota: O PDF da OS concluída é gerado automaticamente no método write()
            # quando o estado muda para 'done', então não é necessário chamar
            # generate_report_and_attach() aqui novamente
            for record in self:
                request_service = record.request_service_id or record.request_id
                if request_service:
                    request_service.finish_request()
                    _logger.debug("Concluída Solicitação: %s" % request_service.name)
                else:
                    _logger.debug("Não existe solicitação para OS %s. Continuando..." % record.name)
      


                                   
      
    def finish_report(self):
        _logger.debug("Procurando relatorios...")
        if self.relatorios_id:
            for rec in self.relatorios_id:
                rec.state = 'done'
        return True

    # utilizado na venda para atorizar Ordem de serviço
    
    def approve(self):
        """
        Aprova a ordem de serviço, mudando seu estado para 'execution_ready'.
        Envia notificação para o parceiro configurado.
        """
        _logger.debug("Aprovando OS: %s", self.name)
        for item in self:
            if item.state != 'done':
                item.write({'state': 'execution_ready'})
                item.message_post(
                    body="A cotação foi aprovada pelo cliente, favor agendar execução",
                    subject="Ordem Aprovada",
                    # TODO: Substituir partner_ids=[3] por uma configuração dinâmica
                    partner_ids=[3]
                )
        _logger.debug("Estado da OS após aprovação: %s", self.state)


    # def add_service(self):
    #     """
    #         Adiciona serviço de acordo com a OS
    #         Verifica se equipamento em garantia, serviço em contrato e coloca o serviço adequado
    #     """
    #     _logger.debug("adicionando serviço...")
      
    #     _logger.debug("procurando serviço já adicionados na OS")

    #     added_services = self.env['engc.os.servicos.line'].search([('os_id', '=',self.id )], offset=0, limit=None, order=None, count=False)
    #     servicos_line = []

    #     _logger.debug("Serviços achados para OS")
    #     for serv_line in added_services: 
    #         servicos_line.append(serv_line.product_id)
    #         _logger.debug(serv_line.product_id.name)
        
          
    #     _logger.debug("Serviços Padrão")
    #     service_default = self.env['product.product'].search([('name','ilike','Manutenção Geral')], limit=1)
    #     _logger.debug(service_default.name)
    
    #     if not service_default.id:
    #         raise UserError(_("Serviço padrão não configurado. Favor configurá-lo. Adicione o serviço 'Manutenção Geral'"))
    #     product_id = service_default
        
            
    #     if self.contrato.id:
    #         _logger.debug("Mudando serviço pois existe contrato para esse equipamento:")
    #         _logger.debug("Colocando serviço padrão para contrato:")
    #         if self.contrato.service_product_id.id:
    #             #verificando se tem esse serviço ja foi adicionado
    #             if self.contrato.service_product_id in servicos_line:
    #                 _logger.debug("Já existe serviço adicionado: %s", self.contrato.service_product_id.name)
    #             else:
    #                 _logger.debug("Serviço adicionado: %s", self.contrato.service_product_id.name)
    #                 product_id = self.contrato.service_product_id
    #     if self.is_warranty:
    #         if self.warranty_type == "fabrica":
    #             _logger.debug("Serviço em garantia fabrica")
    #             service_warranty = self.env['product.product'].search([('name','ilike','Serviço em garantia de fábrica')], limit=1)
    #             if not service_warranty.id:
    #                 raise UserError(_("Serviço garantia não configurado. Favor configurá-lo. Adicione o serviço 'Serviço em garantia de fábrica'"))
                
    #         else:
    #             _logger.debug("Serviço em garantia própria")
    #             service_warranty = self.env['product.product'].search([('name','ilike','Serviço em garantia')], limit=1)
    #             if not service_warranty.id:
    #                 raise UserError(_("Serviço garantia não configurado. Favor configurá-lo. Adicione o serviço 'Serviço em garantia'"))

    #         product_id= service_warranty
            
    #     _logger.debug("Verificando tempo para adicionar no serviço")
    #     if self.time_execution > 0:
    #         _logger.debug("Colocado tempo de execução no serviço: %s",self.time_execution )
    #         product_uom_qty = self.time_execution
            
    #     else:
    #         _logger.debug("Colocado tempo estimado no serviço: %s", self.maintenance_duration)
    #         product_uom_qty = self.maintenance_duration
    #     _logger.debug("Create servicos line:")

    #     if self.description:
    #         name = self.description
    #     else:
    #         name = product_id.display_name

    #     if len(servicos_line) == 0:
    #         _logger.debug("Serviços sera adicionado")
    #         self.servicos = [(0,0,{
    #                 'os_id' : self.id,
    #                 'automatic': True,
    #                 'name': name,
    #                 'product_id' : product_id.id,
    #                 'product_uom': product_id.uom_id.id,
    #                 'product_uom_qty' : product_uom_qty
    #             })]
    #         _logger.debug( self.servicos)
    #     else: 
    #         _logger.debug("Serviços sera apenas atualizado")
    #         for servico in added_services:
             
    #             if servico.automatic:
    #                 _logger.debug("Encontrado servicos adicionados automaticamente, atualizando")
    #                 self.servicos = [(1,servico.id,{
    #                         'os_id' : self.id,
    #                         'automatic': True,
    #                         'name': name,
    #                         'product_id' : product_id.id,
    #                         'product_uom': product_id.uom_id.id,
    #                         'product_uom_qty' : product_uom_qty
    #                     })]

    #     return self.servicos

    def create_checklist(self):
        """
        Cria a lista de verificação (checklist) para OS de manutenção preventiva, 
        comodato ou calibração.
        
        Raises:
            ValidationError: Se não houver equipamento definido, plano de manutenção,
                           ou se o checklist já existir.
        """
        tipos_com_checklist = ['preventive', 'loan', 'calibration']
        
        if self.maintenance_type not in tipos_com_checklist:
            return
        
        _logger.debug("Criando Checklist para OS: %s", self.name)
        
        if not self.equipment_id:
            raise ValidationError(_("Não está definido o campo equipamento na OS"))
        
        maintenance_plan = self.equipment_id.get_maintenance_plan()
        if not maintenance_plan:
            raise ValidationError(
                _("Não há plano de manutenção configurado no equipamento ou na sua categoria")
            )
        
        # Verifica se o checklist já existe
        existing_checklist = self.env['engc.os.verify.checklist'].search(
            [('os_id', '=', self.id)], limit=1
        )
        if existing_checklist:
            raise ValidationError(_("Check list já criado."))
        
        # Filtra as instruções baseadas nas periodicidades selecionadas
        periodicity_ids = self.periodicity_ids.mapped('id')
        instructions = maintenance_plan.instrucion_ids.filtered_domain(
            [('periodicity', 'in', periodicity_ids)]
        )
        
        _logger.debug("Instruções encontradas: %s", instructions.mapped('display_name'))
        
        # Cria os itens do checklist
        checklist_vals = []
        for sequence, instruction in enumerate(instructions):
            checklist_item = {
                'sequence': sequence,
                'os_id': self.id,
                'instruction': instruction.name,
                'section': instruction.section.id if instruction.section else False,
                # Copia informações de medição da instrução para o checklist
                'tem_medicao': instruction.is_measurement if instruction.is_measurement else False,
                'tipo_de_campo': instruction.tipo_de_campo if instruction.tipo_de_campo else 'checkbox',
            }
            
            # Copia a grandeza se for medição
            if instruction.is_measurement and instruction.magnitude:
                checklist_item['magnitude'] = instruction.magnitude.name
            
            checklist_vals.append(checklist_item)
        
        if checklist_vals:
            self.env['engc.os.verify.checklist'].create(checklist_vals)
            _logger.debug("Checklist criado com %d itens", len(checklist_vals))
                

    def generate_report_and_attach(self):
        """
        Gera o PDF do relatório da OS concluída e anexa como mensagem.
        """
        report_name = 'engc_os.report_os_template'
        
        for record in self:
            try:
                report = self.env['ir.actions.report']
                pdf_result = report._render_qweb_pdf(report_name, [record.id])
                
                if pdf_result and pdf_result[0]:
                    filename = f"{record.name}_concluida.pdf"
                    record.message_post(
                        attachments=[(filename, pdf_result[0])],
                        body=_("OS concluída - Relatório gerado automaticamente."),
                    )
                    _logger.debug("PDF gerado e anexado para OS: %s", record.name)
                else:
                    _logger.warning("Falha ao gerar PDF para OS: %s", record.name)
            except Exception as e:
                _logger.error("Erro ao gerar PDF para OS %s: %s", record.name, str(e))
                # Não levanta exceção para não bloquear a conclusão da OS

    def write(self, vals):
        """
        Sobrescreve o método write para:
        - Registrar datas de assinatura quando assinaturas são adicionadas
        - Gerar e anexar PDF quando a OS é concluída
        
        Args:
            vals: Dicionário com os valores a serem escritos.
            
        Returns:
            bool: True se a operação foi bem-sucedida.
        """
        # Verifica se a OS está sendo concluída
        os_being_concluded = vals.get('state') == 'done'
        
        result = super(EngcOs, self).write(vals)
        
        # Atualiza a data de assinatura do técnico quando a assinatura é adicionada pela primeira vez
        if 'signature' in vals and vals.get('signature'):
            records_with_signature = self.filtered(
                lambda r: r.signature and not r.technician_signature_date
            )
            if records_with_signature:
                records_with_signature.write({
                    'technician_signature_date': fields.Datetime.now()
                })
        
        # Atualiza a data de assinatura do supervisor quando a assinatura é adicionada pela primeira vez
        if 'signature2' in vals and vals.get('signature2'):
            records_with_signature2 = self.filtered(
                lambda r: r.signature2 and not r.supervisor_signature_date
            )
            if records_with_signature2:
                records_with_signature2.write({
                    'supervisor_signature_date': fields.Datetime.now()
                })
        
        # Se a OS foi concluída, gera e anexa o PDF
        # Nota: O PDF também é gerado no action_repair_end, mas isso garante que seja gerado
        # mesmo se a OS for concluída por outro método
        if os_being_concluded:
            self.generate_report_and_attach()
            
            # Atualiza a preventiva relacionada se a OS for de manutenção preventiva
            for record in self:
                if record.maintenance_type == 'preventive':
                    # Busca a preventiva relacionada através do campo os_id
                    preventiva = self.env['engc.preventive'].search([
                        ('os_id', '=', record.id)
                    ], limit=1)
                    
                    if preventiva:
                        preventiva.write({
                            'state': 'done',
                            'preventiva_executada': True,
                            'data_execucao': record.date_start if record.date_start else fields.Datetime.now(),
                            'data_execucao_fim': record.date_finish if record.date_finish else fields.Datetime.now(),
                        })
                        _logger.info("Preventiva %s (ID: %s) atualizada para 'concluída' após finalização da OS %s", 
                                   preventiva.name, preventiva.id, record.name)
                    else:
                        _logger.warning("OS %s (ID: %s) é de manutenção preventiva mas não foi encontrada preventiva relacionada", 
                                      record.name, record.id)
        
        return result

    