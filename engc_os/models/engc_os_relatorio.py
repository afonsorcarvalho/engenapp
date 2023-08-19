import time
from datetime import date, datetime, timedelta

from odoo import models, fields,  api, _, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
from odoo import netsvc
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class RelatoriosLine(models.Model):
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

#TODO 
#   1 -Fazer codigo para gerar o codigo name somente quando salvar o relatório

    state = fields.Selection(string='', selection=STATE_SELECTION, default="draft",
    required=True
    )
    report_type = fields.Selection(string='Tipo de Relatório', selection=REPORT_TYPE, 
    required=True
    )

    company_id = fields.Many2one(
        string='Instituição', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
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
        if 'company_id' in vals:
            vals['name'] = self.env['ir.sequence'].with_context(force_company=self.env.user.company_id.id).next_by_code(
                'engc.os.relatorio_sequence') or _('New')
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code('engc.os.relatorio_sequence') or _('New')
        

        result = super(RelatoriosLine, self).create(vals)
        return result
        
    os_id = fields.Many2one(
        'engc.os', 'Ordem de Serviço',
        index=True, ondelete='cascade',required=True)
    #TODO colocar tecnico na Os automaticamente, a media que ele vai
    #  sendo inserido aqui nos relatórios
    technicians  = fields.Many2many(
        string='Técnicos',
        comodel_name='hr.employee'
       
    )
    
    
    
    service_summary = fields.Text("Resumo do atendimento")
    fault_description = fields.Text("Descrição do defeito")
    
    pendency = fields.Text("Pendência")
    observations = fields.Text("Observações")


    data_atendimento = fields.Date(string='Data de Atendimento', 
        required=True
    )

    start_hour = fields.Float("Hora início", 
        required=True
    )
    final_hour = fields.Float("Hora fim", 
        required=True
    )
    picture_ids = fields.One2many('engc.os.relatorios.pictures', 'relatorio_id', "fotos")

    #******************************************
    #  ACTIONS
    #
    #******************************************
    

    def action_cancel(self):
        self.write({
            'state': 'cancel'
        })

    def action_done(self):
         self.write({
            'state': 'done'
        })
 

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
        default=lambda self: self.env.user.company_id
    )
    relatorio_id = fields.Many2one(
        string='Equipamento', 
        comodel_name='engc.os.relatorios', 
        required=True, 
       
    )
    picture = fields.Binary(string="Foto", 
    required=True
     )
