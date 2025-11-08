# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class RelatorioAtendimentoResumoWizard(models.TransientModel):
    """
    Wizard para gerar relatório resumido de relatórios de atendimento.
    
    Permite filtrar por equipamento, período de datas e status.
    """
    _name = 'wizard.relatorio.atendimento.resumo'
    _description = 'Wizard para Relatório Resumido de Atendimentos'

    equipment_id = fields.Many2one(
        'engc.equipment',
        string='Equipamento',
        help='Filtrar por equipamento específico (opcional)'
    )
    
    date_start = fields.Datetime(
        string='Data Início',
        required=True,
        default=lambda self: datetime.now() - timedelta(days=30),
        help='Data inicial para filtrar os relatórios'
    )
    
    date_end = fields.Datetime(
        string='Data Fim',
        required=True,
        default=fields.Datetime.now,
        help='Data final para filtrar os relatórios'
    )
    
    state = fields.Selection(
        [
            ('draft', 'Criado'),
            ('done', 'Concluído'),
            ('cancel', 'Cancelado'),
        ],
        string='Status',
        default=False,
        help='Filtrar por status do relatório (opcional)'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Instituição',
        default=lambda self: self.env.company,
        required=True
    )

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        """Valida que a data início seja anterior à data fim."""
        for record in self:
            if record.date_start and record.date_end:
                if record.date_start > record.date_end:
                    raise ValidationError(
                        _('⚠️ A Data Início deve ser anterior à Data Fim.')
                    )

    def action_gerar_relatorio(self):
        """
        Gera o relatório resumido com base nos filtros selecionados.
        
        Returns:
            dict: Action para abrir o relatório PDF
        """
        self.ensure_one()
        
        # Monta o domain dinamicamente - obrigatórios: date_start e date_end
        domain = [
            ('data_atendimento', '>=', self.date_start),
            ('data_atendimento', '<=', self.date_end),
        ]
        
        # Adiciona filtros opcionais ao domain
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        
        if self.equipment_id:
            domain.append(('equipment_id', '=', self.equipment_id.id))
        
        # Só adiciona state ao domain se houver seleção (não False, não None, não string vazia)
        if self.state and self.state in ['draft', 'done', 'cancel']:
            domain.append(('state', '=', self.state))
        
        # Log para debug
        _logger.debug("="*50)
        _logger.debug("Filtros aplicados:")
        _logger.debug("  Data início: %s", self.date_start)
        _logger.debug("  Data fim: %s", self.date_end)
        _logger.debug("  Instituição: %s", self.company_id.name if self.company_id else "Todos")
        _logger.debug("  Equipamento: %s", self.equipment_id.name if self.equipment_id else "Todos")
        _logger.debug("  Status: %s", self.state if self.state else "Todos")
        _logger.debug("Domain completo: %s", domain)
        
        # Busca os relatórios filtrados
        relatorios = self.env['engc.os.relatorios'].search(domain, order='data_atendimento desc')
        
        _logger.debug("Relatórios encontrados: %d", len(relatorios))
        if relatorios:
            _logger.debug("Primeiros relatórios: %s", [str(r.name) for r in relatorios[:5]])
        _logger.debug("="*50)
        
        if not relatorios:
            raise UserError(
                _('⚠️ Nenhum relatório de atendimento encontrado com os filtros selecionados.')
            )
        
        # Prepara os dados para o relatório
        data = {
            'equipment_id': self.equipment_id.id if self.equipment_id else False,
            'date_start': self.date_start.strftime('%d/%m/%Y %H:%M') if self.date_start else False,
            'date_end': self.date_end.strftime('%d/%m/%Y %H:%M') if self.date_end else False,
            'state': self.state if self.state else False,
        }
        
        # Log dos IDs que serão passados
        _logger.debug("IDs dos relatórios que serão passados para o relatório: %s", relatorios.ids)
        
        # Busca o relatório registrado
        report = self.env.ref('engc_os.report_relatorio_atendimento_resumo')
        
        # Prepara o contexto com os dados para o nome do arquivo
        # IMPORTANTE: Não sobrescrever active_ids aqui, o report_action faz isso automaticamente
        context = self.env.context.copy()
        context['report_data'] = data
        if self.company_id:
            context['company_id'] = self.company_id.id
        
        # Retorna a ação para gerar o relatório
        # O report_action automaticamente adiciona os docids como active_ids no contexto
        action = report.with_context(context).report_action(relatorios.ids, data=data)
        
        # Log para debug
        _logger.debug("Action retornada: %s", action)
        _logger.debug("Context na action: %s", action.get('context', {}).get('active_ids', []))
        
        return action

