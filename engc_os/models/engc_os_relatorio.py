import time
from datetime import date, datetime, timedelta

from odoo import models, fields,  api, _, Command, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
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
    
    
            

    @api.model
    def create(self, vals):
        """Salva ou atualiza os dados no banco de dados"""
        # for vals in vals_list:

       # self._verify_relatorio_aberto()
        if 'company_id' in vals:
            vals['name'] = self.env['ir.sequence'].with_company(vals['company_id']).next_by_code(
                'engc.os.relatorio_sequence') or _('New')
        else:
            vals['name'] = self.env['ir.sequence'].with_company(self.company_id).next_by_code(
                'engc.os.relatorio_sequence') or _('New')

        result = super(Relatorios, self).create(vals)
        return result

    os_id = fields.Many2one(
        'engc.os', 'Ordem de Serviço',
        ondelete='cascade', index=True)
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
        print(self)
        self.request_parts_count = self.env['engc.os.request.parts'].search_count(
            [('relatorio_request_id', '=', self.id)])
        
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
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'engc.os.request.parts',
            'target': 'new',
            'context': {
                 'default_os_id': self.os_id.id,
                 'default_relatorio_request_id': self.id,

                          },
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
        self.write({
            'state': 'done'
        })


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
