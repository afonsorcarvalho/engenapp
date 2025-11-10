import time
from datetime import date, datetime, timedelta

from odoo import models, fields,  api, _, Command, SUPERUSER_ID
#from odoo.addons import decimal_precision as dp
from odoo import netsvc
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class Relatorios(models.Model):
    _name = 'engc.os.relatorios'
    _description = 'Relatórios de atendimento'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "data_atendimento,id"
    _check_company_auto = True

    STATE_SELECTION = [
        ('draft', 'Criado'),
        ('done', 'Concluído'),
        ('cancel', 'Cancelado'),
    ]
    REPORT_TYPE = [
        ('orcamento', 'Orçamento'),
        ('manutencao', 'Manutenção'),
        ('instalacao', 'Instalação'),
        ('treinamento', 'Treinamento'),
        ('calibracao', 'Calibração'),
        ('qualificacao', 'Qualificação'),

    ]
    STATE_EQUIPMENT_SELECTION = [ 
        ('parado', 'Parado'),
        ('funcionando', 'Funcionando'),
        ('restricao', 'Funcionando com restrições'),
    ]

# TODO
#   1 -Fazer codigo para gerar o codigo name somente quando salvar o relatório

    state = fields.Selection(string='', selection=STATE_SELECTION, default="draft",
                             required=True
                             )
    report_type = fields.Selection(string='Tipo de Relatório', selection=REPORT_TYPE,
                                   required=True)

    # company_id = fields.Many2one(
    #     related='os_id.company_id', store=True, readonly=True, precompute=True,
    #     index=True,

    # )
    company_id = fields.Many2one(
        string='Instituição',
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company
    )
    name = fields.Char(
        'Nº Relatório de Serviço',
        default=lambda self: _('New'), copy=False,
        readonly=True,
        index=True,
        required=True)
    
    
            

    @api.model_create_multi
    def create(self, vals_list):
        """Salva ou atualiza os dados no banco de dados"""
        # Processa cada registro na lista
        for vals in vals_list:
            # Valida que a ordem de serviço é obrigatória
            if not vals.get('os_id'):
                raise ValidationError(
                    _('⚠️ É obrigatório informar a Ordem de Serviço para criar um relatório de atendimento.')
                )
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_company(vals['company_id']).next_by_code(
                    'engc.os.relatorio_sequence') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].with_company(self.env.company).next_by_code(
                    'engc.os.relatorio_sequence') or _('New')

        result = super(Relatorios, self).create(vals_list)
        # Aciona validações na OS após criar relatório
        # Recalcula os campos computados antes de validar
        for relatorio in result:
            if relatorio.os_id:
                # Força o recálculo dos campos computados
                relatorio.os_id._compute_date_start()
                relatorio.os_id._compute_date_finish()
                # Aciona as validações
                relatorio.os_id._check_date_start_vs_finish()
                relatorio.os_id._check_date_request_vs_start()
            
            # Se há checklist_item_ids, define o relatorio_id nos itens do checklist
            if relatorio.checklist_item_ids:
                relatorio.checklist_item_ids.write({'relatorio_id': relatorio.id})
        return result
    
    def write(self, vals):
        """
        Sobrescreve o método write para acionar validações na OS 
        quando os campos de data dos relatórios forem alterados.
        Também limpa os checks quando itens são removidos do checklist do relatório
        e atualiza o resumo do atendimento.
        """
        # Flag para indicar se houve remoção de itens do checklist
        checklist_items_removed = False
        
        # Se checklist_item_ids foi alterado, verifica se algum item foi removido
        if 'checklist_item_ids' in vals:
            for relatorio in self:
                # Guarda os IDs atuais antes da modificação
                old_checklist_ids = set(relatorio.checklist_item_ids.ids)
                
                # Processa os comandos do many2many para identificar remoções
                for command in vals['checklist_item_ids']:
                    # Comando (3, id) ou (2, id) remove o item
                    if command[0] in (2, 3):
                        removed_item_id = command[1]
                        # Limpa o check e medições do item removido
                        removed_item = self.env['engc.os.verify.checklist'].browse(removed_item_id)
                        removed_item.write({
                            'check': False,
                            'medicao': 0.0,
                            'observations': '',
                            'relatorio_id': False
                        })
                        checklist_items_removed = True
                    # Comando (5,) ou (6, 0, [ids]) substitui todos
                    elif command[0] == 5:
                        # Remove todos - limpa todos os itens atuais
                        for item in relatorio.checklist_item_ids:
                            item.write({
                                'check': False,
                                'medicao': 0.0,
                                'observations': '',
                                'relatorio_id': False
                            })
                        checklist_items_removed = True
                    elif command[0] == 6:
                        # Substitui por nova lista - limpa os que não estão na nova lista
                        new_ids = set(command[2])
                        removed_ids = old_checklist_ids - new_ids
                        if removed_ids:
                            removed_items = self.env['engc.os.verify.checklist'].browse(list(removed_ids))
                            removed_items.write({
                                'check': False,
                                'medicao': 0.0,
                                'observations': '',
                                'relatorio_id': False
                            })
                            checklist_items_removed = True
        
        result = super(Relatorios, self).write(vals)
        
        # Se as datas de atendimento foram alteradas, aciona validações na OS
        if 'data_atendimento' in vals or 'data_fim_atendimento' in vals:
            # Agrupa as OSs para evitar validações duplicadas
            os_ids = self.mapped('os_id').filtered(lambda os: os.id)
            for os_record in os_ids:
                # Força o recálculo dos campos computados
                os_record._compute_date_start()
                os_record._compute_date_finish()
                # Aciona as validações
                os_record._check_date_start_vs_finish()
                os_record._check_date_request_vs_start()
        
        # Se checklist_item_ids foi alterado, atualiza o relatorio_id nos novos itens
        if 'checklist_item_ids' in vals:
            for relatorio in self:
                if relatorio.checklist_item_ids:
                    relatorio.checklist_item_ids.write({'relatorio_id': relatorio.id})
                
                # Se houve remoção de itens, atualiza o resumo do atendimento
                if checklist_items_removed:
                    relatorio._update_summary_from_checklist()
        
        return result
    
    @api.onchange('os_id')
    def _onchange_os_id_load_checklist(self):
        """
        Carrega automaticamente os itens do checklist da OS quando a OS é selecionada.
        Filtra apenas os itens que ainda não foram marcados como realizados.
        Para OS preventiva, preenche automaticamente descrição do defeito e resumo do atendimento.
        """
        if self.os_id:
            # Se for manutenção preventiva, preenche os campos automaticamente
            if self.os_id.maintenance_type == 'preventive':
                # Preenche a descrição do defeito
                self.fault_description = "Manutenção Preventiva"
                
                # Monta o resumo do atendimento com as periodicidades
                if self.os_id.periodicity_ids:
                    periodicity_names = self.os_id.periodicity_ids.mapped('name')
                    periodicity_str = ', '.join(periodicity_names)
                    self.service_summary = f"Realizada a Preventiva ({periodicity_str}) seguindo o check-list de preventiva do equipamento."
                else:
                    self.service_summary = "Realizada a Preventiva seguindo o check-list de preventiva do equipamento."
            
            # Carrega o checklist se existir
            if self.os_id.check_list_id:
                # Filtra apenas os itens do checklist que ainda não foram marcados
                unchecked_items = self.os_id.check_list_id.filtered(lambda item: not item.check)
                
                if unchecked_items:
                    checklist_ids = unchecked_items.ids
                    self.checklist_item_ids = [(6, 0, checklist_ids)]
                    # Define o relatorio_id nos itens do checklist para atualização automática do resumo
                    # Isso só funciona se o relatório já existir (já foi salvo)
                    if self.id:
                        self.env['engc.os.verify.checklist'].browse(checklist_ids).write({
                            'relatorio_id': self.id
                        })
                else:
                    # Se todos os itens já foram checados, não carrega nenhum item
                    self.checklist_item_ids = [(5, 0, 0)]
    
    def _update_summary_from_checklist(self):
        """
        Atualiza o resumo do atendimento com base nos itens do checklist marcados neste relatório.
        """
        self.ensure_one()
        if not self.checklist_item_ids:
            return

        # Coleta os itens marcados do checklist neste relatório
        checked_items = self.checklist_item_ids.filtered(lambda item: item.check)

        # Monta o texto do resumo com os itens marcados
        summary_lines = []
        for item in checked_items.sorted('sequence'):
            line = f"- {item.instruction}"
            if item.observations:
                line += f" ({item.observations})"
            if item.tem_medicao and item.medicao:
                magnitude = f" {item.magnitude}" if item.magnitude else ""
                line += f" - Medição: {item.medicao}{magnitude}"
            
            summary_lines.append(line)

        # Atualiza o resumo do atendimento
        checklist_summary = "\n".join(summary_lines)
        current_summary = self.service_summary or ""

        # Remove o resumo anterior do checklist se existir
        if "Checklist realizado:" in current_summary:
            parts = current_summary.split("Checklist realizado:")
            base_summary = parts[0].strip()
            if checked_items:
                if base_summary:
                    self.service_summary = f"{base_summary}\n\nChecklist realizado:\n{checklist_summary}"
                else:
                    self.service_summary = f"Checklist realizado:\n{checklist_summary}"
            else:
                # Se não há itens marcados, remove a seção do checklist
                self.service_summary = base_summary
        else:
            if checked_items:
                if current_summary:
                    self.service_summary = f"{current_summary}\n\nChecklist realizado:\n{checklist_summary}"
                else:
                    self.service_summary = f"Checklist realizado:\n{checklist_summary}"
    
    def action_update_summary_from_checklist(self):
        """
        Método público para atualizar o resumo do atendimento com base nos itens do checklist marcados.
        """
        self._update_summary_from_checklist()

    os_id = fields.Many2one(
        'engc.os', 'Ordem de Serviço',
        ondelete='cascade', index=True, required=True)
    
    equipment_id = fields.Many2one(
        'engc.equipment',
        string='Equipamento',
        related='os_id.equipment_id',
        store=True,
        readonly=True,
        help='Equipamento associado através da Ordem de Serviço'
    )
    
    maintenance_type = fields.Selection(
        string='Tipo de Manutenção',
        related='os_id.maintenance_type',
        store=True,
        readonly=True,
        help='Tipo de manutenção da Ordem de Serviço'
    )
    
    # TODO colocar tecnico na Os automaticamente, a media que ele vai
    #  sendo inserido aqui nos relatórios
    technicians = fields.Many2many(
        string='Técnicos',
        comodel_name='hr.employee',
        required=True,
        check_company=True)

    service_summary = fields.Text("Resumo do atendimento",
                                  required=True)
    fault_description = fields.Text("Descrição do defeito",
                                    required=True)
    
    # Campo para referenciar os itens do checklist da OS
    checklist_item_ids = fields.Many2many(
        string='Itens do Checklist',
        comodel_name='engc.os.verify.checklist',
        relation='relatorio_checklist_rel',
        column1='relatorio_id',
        column2='checklist_id',
        domain="[('os_id', '=', os_id)]",
        help='Itens do checklist da Ordem de Serviço que podem ser editados neste relatório'
    )

    pendency = fields.Text("Pendência")
    state_equipment = fields.Selection(
        string="Estado do Equipamento", selection=STATE_EQUIPMENT_SELECTION,  tracking=True)
    restriction_type = fields.Text("Restrição")
    observations = fields.Text("Observações")

    data_atendimento = fields.Datetime(string='Data de Atendimento',
                                       required=True
                                       )
    data_fim_atendimento = fields.Datetime(string='Fim do Atendimento',
                                           required=True
                                           )
    time_execution = fields.Float(compute="_compute_time_execution")
    
    @api.depends("data_atendimento","data_fim_atendimento")
    def _compute_time_execution(self):
        
        for record in self:
            if record.data_atendimento and record.data_fim_atendimento:
                diferenca = record.data_fim_atendimento - record.data_atendimento
                record.time_execution = diferenca.total_seconds() / 3600.0  # Converte para horas
            else:
                record.time_execution = 0.0  # Se algum valor for nulo, define como 0
    
    # ******************************************
    #  VALIDAÇÕES (CONSTRAINTS)
    #
    # ******************************************
    
    @api.constrains('os_id')
    def _check_os_id_required(self):
        """
        Valida que o relatório de serviço deve ter uma ordem de serviço associada.
        """
        for record in self:
            if not record.os_id:
                raise ValidationError(
                    _('⚠️ É obrigatório informar a Ordem de Serviço para criar um relatório de atendimento.')
                )
    
    @api.constrains('data_atendimento', 'data_fim_atendimento')
    def _check_data_atendimento_vs_fim(self):
        """
        Valida que a Data de Atendimento deve ser antes do Fim do Atendimento.
        """
        for record in self:
            if record.data_atendimento and record.data_fim_atendimento:
                if record.data_atendimento >= record.data_fim_atendimento:
                    raise ValidationError(
                        _('A Data de Atendimento deve ser anterior ao Fim do Atendimento.\n'
                          'Data de Atendimento: %s\n'
                          'Fim do Atendimento: %s') % (
                            record.data_atendimento.strftime('%d/%m/%Y %H:%M:%S'),
                            record.data_fim_atendimento.strftime('%d/%m/%Y %H:%M:%S')
                        )
                    )
        
    start_hour = fields.Float("Hora início",

                              )
    final_hour = fields.Float("Hora fim",

                              )
    

    request_parts = fields.One2many(
        'engc.os.request.parts', 'relatorio_request_id', check_company=True)
    
    request_parts_count = fields.Integer(compute="compute_request_parts_count")

    request_services = fields.One2many(
        'engc.os.request.parts', 'relatorio_request_id', check_company=True)
    
    request_services_count = fields.Integer(compute="compute_request_services_count")

    @api.depends("request_parts")
    def compute_request_parts_count(self):
        """
        Calcula o total de peças manipuladas pelo relatório (requisitadas e aplicadas).
        """
        for relatorio in self:
            # Busca todas as peças relacionadas ao relatório (requisitadas ou aplicadas)
            # Remove duplicatas contando apenas uma vez se a peça foi requisitada e aplicada no mesmo relatório
            all_parts = self.env['engc.os.request.parts'].search([
                '|',
                ('relatorio_request_id', '=', relatorio.id),
                ('relatorio_application_id', '=', relatorio.id)
            ])
            relatorio.request_parts_count = len(all_parts)
        
    @api.depends("request_services")
    def compute_request_services_count(self):
        print(self)
        self.request_services_count = self.env['engc.os.request.parts'].search_count(
            [('relatorio_request_id', '=', self.id)])

    request_applicated_parts = fields.One2many(
        'engc.os.relatorios.request_application.parts', 'relatorio_id', check_company=True)

    @api.depends("request_parts")
    def _compute_request_parts_ids(self):
        print(self)
        self.request_parts = self.env['engc.os.request.parts'].search(
            [('os_id', '=', self.os_id.id)])

    def _inverse_request_parts_ids(self):
        _logger.info(self)

    picture_ids = fields.One2many('engc.os.relatorios.pictures',
                                  'relatorio_id', "fotos", ondelete='cascade', check_company=True)

    def _get_parts_report(self, type, state):
        """
        Esta função é responsável por buscar e retornar partes de relatórios associadas a uma ordem de serviço (OS) com base no tipo e estado especificados.

        Args:
            type (str): O tipo a ser buscado ('application' ou 'request').
            state (str): O estado das partes do relatório a serem buscadas.

        Returns:
            recordset: Um conjunto de registros contendo as peças de relatório correspondentes à  relatorio de OS, tipo e estado fornecidos.

        Exemplo:
            Para buscar todas as peças de relatório do tipo 'application' com estado 'aplicada' para uma OS específica:
            parts = self._get_parts_report('application', 'aplicada')
        """
        domain = []
        if type == 'application':
            type_relatorio = 'relatorio_application_id'
            domain = [
                ('os_id', '=', self.os_id.id),
                ('state', '=', state),
                (type_relatorio, '=', self.id)]
        if type == 'request':
            type_relatorio = 'relatorio_request_id'
            domain = [
                ('os_id', '=', self.os_id.id),
                (type_relatorio, '=', self.id)]

        result = self.env['engc.os.request.parts'].search(domain)
        return result

    # ******************************************
    #  ACTIONS
    #
    # ******************************************

    def action_go_request_parts(self):
        """
        Abre a visualização de todas as peças manipuladas por este relatório.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Peças'),
            'view_mode': 'tree,form',
            'res_model': 'engc.os.request.parts',
            'domain': [
                '|',
                ('relatorio_request_id', '=', self.id),
                ('relatorio_application_id', '=', self.id)
            ],
            'context': {
                'default_os_id': self.os_id.id,
                'default_relatorio_request_id': self.id,
                'create': False if self.state == 'done' else True,
                'edit': False if self.state == 'done' else True,
                'delete': False if self.state == 'done' else True,
            },
        }
    def action_go_request_services(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Peças'),
            'view_mode': 'tree,form',
            'res_model': 'engc.os.request.parts',
            'domain': [('relatorio_request_id', '=', self.id)],
            'context': {
                'default_os_id': self.os_id.id,
                'default_relatorio_request_id': self.id,
                'create': False if self.state == 'done' else True,
                'edit': False if self.state == 'done' else True,
                'delete': False if self.state == 'done' else True,

            },
        }

    def action_add_request_parts(self):
        _logger.info("Requisitar peças")
       
        return {
            'name': _('Requisitar Peças'),
            'type': 'ir.actions.act_window',
            'views': [[False,'tree']],
            'view_mode': 'tree',
            'res_model': 'engc.os.request.parts',
            'target': 'new',
            'context': {
                 'default_os_id': self.os_id.id,
                 'default_relatorio_request_id': self.id,
                 'create': False if self.state == 'done' else True,
                 'edit': False if self.state == 'done' else True,
                 'delete': False if self.state == 'done' else True,

                          },
            'domain':[('relatorio_request_id','=',self.id)]
        }
    def _get_parts_requests(self):
        result = self.env['engc.os.request.parts'].search([
            ('os_id', '=', self.os_id.id),
            ('state', 'in', ['requisitada']),

        ])
        _logger.debug("Lista de peças requisitadas:")
        _logger.debug(result)
        result = result.mapped('id')
        return result

    def action_application_parts(self):
        _logger.info("Aplicar peças")

        return {
            'name': _('Aplicar Peças'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'application.parts.wizard',
            'target': 'new',
            'context': {
                'default_os_id': self.os_id.id,
                'default_relatorio_id': self.id,
                'default_list_parts_request': [
                    Command.create({'application_parts_wizard': self.id, 'request_parts': line_vals}) for line_vals in self._get_parts_requests()]
            }
        }

    def action_cancel(self):
        self.write({
            'state': 'cancel'
        })
        

    def action_done(self):
        """
        Marca o relatório como concluído e cria requisições de estoque para as peças requisitadas.
        """
        self.write({
            'state': 'done'
        })
        
        # Cria requisições de estoque para as peças requisitadas neste relatório
        self._create_stock_requests()
    
    def _create_stock_requests(self):
        """
        Cria requisições de estoque para as peças requisitadas no relatório.
        """
        self.ensure_one()
        
        # Verifica se o módulo stock.request está disponível
        try:
            StockRequest = self.env['stock.request']
        except KeyError:
            _logger.warning("Módulo stock.request não está disponível. Requisições de estoque não serão criadas.")
            return
        
        # Busca todas as peças requisitadas neste relatório
        parts_requested = self.env['engc.os.request.parts'].search([
            ('relatorio_request_id', '=', self.id),
            ('state', 'in', ['requisitada', 'autorizada'])
        ])
        
        if not parts_requested:
            return
        
        # Agrupa peças por produto para evitar duplicatas
        parts_by_product = {}
        for part in parts_requested:
            if not part.product_id:
                continue
            if part.product_id.id not in parts_by_product:
                parts_by_product[part.product_id.id] = {
                    'product_id': part.product_id.id,
                    'quantity': 0.0,
                    'parts': []
                }
            parts_by_product[part.product_id.id]['quantity'] += part.product_uom_qty
            parts_by_product[part.product_id.id]['parts'].append(part)
        
        # Cria uma requisição de estoque para cada produto
        stock_requests_created = []
        for product_id, data in parts_by_product.items():
            try:
                stock_request_vals = {
                    'product_id': data['product_id'],
                    'quantity': data['quantity'],
                    'note': f"Requisição automática do relatório {self.name} - OS: {self.os_id.name if self.os_id else 'N/A'}",
                    'state': 'draft',
                    'company_id': self.company_id.id,
                }
                stock_request = StockRequest.create(stock_request_vals)
                stock_requests_created.append(stock_request)
                _logger.info(f"Requisição de estoque criada: {stock_request.id} para produto {data['product_id']}")
            except Exception as e:
                _logger.error(f"Erro ao criar requisição de estoque para produto {data['product_id']}: {str(e)}")
        
        if stock_requests_created:
            _logger.info(f"Foram criadas {len(stock_requests_created)} requisições de estoque para o relatório {self.name}")


class RelatoriosRequestApplicationParts(models.Model):
    _name = 'engc.os.relatorios.request_application.parts'
    _description = "Requisição de peças"
    _check_company_auto = True

    company_id = fields.Many2one(
        string='Instituição',
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company
    )

    relatorio_id = fields.Many2one(
        string='Relatório',
        comodel_name='engc.os.relatorios',
        required=True,
        check_company=True

    )

    request_parts_id = fields.Many2one('engc.os.request.parts',  'Peças', check_company=True,
                                       #domain=lambda self: [('os_id','=',self.os_id.id)]
                                       )

    @api.constrains('request_parts_id')
    def _check_request_parts_id(self):
        for record in self:
            if len(self.search([('request_parts_id', '=', record.request_parts_id.id)])) > 1:
                raise ValidationError(_("Já foi aplicada essa peça"))

    os_id = fields.Many2one(
        'engc.os', 'Ordem de Serviço',
        index=True, ondelete='cascade', check_company=True)

    placed = fields.Boolean('Aplicada')

    # product_uom_qty = fields.Float(
    # 	'Qtd', default=1.0,
    # 	digits=dp.get_precision('Product Unit of Measure'),
    #      # required=True
    #       )
    # product_uom = fields.Many2one(
    # 	'product.uom', 'Unidade de medida',
    # 	#required=True
    #     )
    # os_id = fields.Many2one(
    # 	'engc.os', 'Ordem de Serviço',
    # 	 ondelete='cascade')


class RelatoriosPictures(models.Model):
    _name = 'engc.os.relatorios.pictures'
    _description = "Fotos do atendimento"
    _check_company_auto = True

    name = fields.Char('Título da foto')
    description = fields.Text('Descrição da foto')

    company_id = fields.Many2one(
        string='Instituição',
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company
    )
    relatorio_id = fields.Many2one(
        string='Relatorio',
        comodel_name='engc.os.relatorios',
        required=True,
        check_company=True

    )
    os_id = fields.Many2one(
        'engc.os', 'Ordem de Serviço',
        index=True, ondelete='cascade', check_company=True)

    picture = fields.Binary(string="Foto",
                            required=True
                            )
    
    def _get_report_base_filename(self):
        """
        Gera o nome base do arquivo do relatório.
        Inclui a instituição e as datas quando disponíveis no contexto.
        """
        self.ensure_one()
        
        # Verifica se há dados de filtro no contexto (vindo do wizard)
        context = self.env.context
        report_data = context.get('report_data') or {}
        
        # Monta o nome base
        nome_base = "Relatorio Resumido de Atendimentos"
        
        # Adiciona a instituição (usa a do primeiro relatório ou do contexto)
        company = self.company_id
        if not company and context.get('company_id'):
            company = self.env['res.company'].browse(context['company_id'])
        if company:
            # Remove caracteres especiais do nome da empresa para o nome do arquivo
            company_name = company.name.replace('/', '-').replace('\\', '-').replace(':', '-')
            nome_base += f" - {company_name}"
        
        # Adiciona as datas se disponíveis
        date_start = report_data.get('date_start')
        date_end = report_data.get('date_end')
        
        if date_start and date_end:
            # Formata as datas (removendo hora se necessário)
            try:
                from datetime import datetime
                if isinstance(date_start, str):
                    # Tenta diferentes formatos
                    try:
                        dt_start = datetime.strptime(date_start, '%d/%m/%Y %H:%M')
                    except:
                        dt_start = datetime.strptime(date_start, '%Y-%m-%d %H:%M:%S')
                else:
                    dt_start = date_start
                if isinstance(date_end, str):
                    try:
                        dt_end = datetime.strptime(date_end, '%d/%m/%Y %H:%M')
                    except:
                        dt_end = datetime.strptime(date_end, '%Y-%m-%d %H:%M:%S')
                else:
                    dt_end = date_end
                
                data_inicio_str = dt_start.strftime('%d%m%Y')
                data_fim_str = dt_end.strftime('%d%m%Y')
                nome_base += f" - {data_inicio_str}_a_{data_fim_str}"
            except Exception as e:
                # Se houver erro na formatação, usa as strings originais (sanitizadas)
                date_start_clean = str(date_start).replace('/', '-').replace(':', '-').replace(' ', '_')
                date_end_clean = str(date_end).replace('/', '-').replace(':', '-').replace(' ', '_')
                nome_base += f" - {date_start_clean}_a_{date_end_clean}"
        
        return nome_base
