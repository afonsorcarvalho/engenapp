# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class CronogramaPreventivaPrintWizard(models.TransientModel):
    _name = 'cronograma.preventiva.print.wizard'
    _description = 'Wizard para Impressão de Cronograma de Preventiva'

    cronograma_id = fields.Many2one(
        'engc.preventive.cronograma',
        string='Cronograma',
        required=True,
        default=lambda self: self._get_default_cronograma()
    )
    
    include_maintenance_plan = fields.Boolean(
        string='Incluir Planos de Manutenção',
        default=False,
        help='Se marcado, o relatório incluirá os planos de manutenção dos equipamentos'
    )
    
    def _get_default_cronograma(self):
        """Pega o cronograma do contexto se houver"""
        return self.env.context.get('active_id', False)
    
    def action_print_cronograma(self):
        """Imprime o cronograma com as opções selecionadas"""
        self.ensure_one()
        
        if not self.cronograma_id:
            raise UserError(_('Por favor, selecione um cronograma.'))
        
        # DEBUG: Log das informações
        _logger.info("=" * 80)
        _logger.info("DEBUG WIZARD - action_print_cronograma")
        _logger.info(f"Ciclo existe? {bool(self.cronograma_id)}")
        _logger.info(f"Cronograma ID: {self.cronograma_id.id if self.cronograma_id else 'NENHUM'}")
        _logger.info(f"Cronograma Name: {self.cronograma_id.name if self.cronograma_id else 'NENHUM'}")
        _logger.info(f"include_maintenance_plan (checkbox): {self.include_maintenance_plan}")
        _logger.info(f"Tipo de include_maintenance_plan: {type(self.include_maintenance_plan)}")
        
        # DEBUG: Tipo de self.cronograma_id
        _logger.info(f"DEBUG: Tipo de self.cronograma_id: {type(self.cronograma_id)}")
        _logger.info(f"DEBUG: self.cronograma_id.ids: {self.cronograma_id.ids}")
        
        # Busca o relatório do wizard
        report = self.env.ref('engc_os.report_cronograma_preventiva_wizard')
        _logger.info(f"DEBUG: Report encontrado: {report.name}")
        _logger.info(f"DEBUG: Report model: {report.model}")
        
        # IMPORTANTE: Passa os IDs para o report_action
        # O AbstractModel _get_report_values vai receber e processar
        # Garante que o contexto tenha active_id e active_model corretos para o print_report_name funcionar
        context = self.env.context.copy()
        context.update({
            'active_id': self.cronograma_id.id,
            'active_ids': self.cronograma_id.ids,
            'active_model': 'engc.preventive.cronograma',
        })
        
        action = report.with_context(context).report_action(
            self.cronograma_id.ids,  # ✅ Passa a lista de IDs
            data={'include_maintenance_plan': self.include_maintenance_plan}
        )
        
        _logger.info(f"DEBUG: Action retornada: {action}")
        _logger.info(f"DEBUG: Action context: {action.get('context', {})}")
        _logger.info("=" * 80)
        
        return action
