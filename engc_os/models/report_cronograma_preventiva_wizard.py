# -*- coding: utf-8 -*-
"""Modelo abstrato para processar dados do Report de Cronograma de Preventiva (Wizard)"""
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class ReportCronogramaPreventivaWizard(models.AbstractModel):
    """
    Modelo abstrato para o relatório de Cronograma de Preventiva (Wizard).
    
    Processa os dados antes de enviar para o template QWeb.
    """
    _name = 'report.engc_os.report_cronograma_preventiva_wizard_template'
    _description = 'Relatório de Cronograma de Preventiva (Wizard)'

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Retorna os valores para o template do relatório.
        
        Args:
            docids: Lista de IDs dos cronogramas de preventiva
            data: Dicionário com include_maintenance_plan (boolean)
        
        Returns:
            dict: Dicionário com 'docs', 'data' e outros valores para o template
        """
        data = data or {}
        
        # Se docids estiver vazio, tenta pegar do contexto (active_ids)
        if not docids:
            active_ids = self.env.context.get('active_ids', [])
            if active_ids:
                docids = active_ids
        
        # Busca os cronogramas
        cronogramas = self.env['engc.preventive.cronograma'].browse(docids) if docids else self.env['engc.preventive.cronograma']
        
        # Obtém o flag de incluir planos de manutenção
        include_maintenance_plan = data.get('include_maintenance_plan', False) or self.env.context.get('include_maintenance_plan', False)
        
        # DEBUG: Log das informações
        _logger.info("=" * 80)
        _logger.info("DEBUG REPORT - _get_report_values")
        _logger.info(f"Cronogramas IDs: {docids}")
        _logger.info(f"Total de cronogramas: {len(cronogramas)}")
        _logger.info(f"include_maintenance_plan: {include_maintenance_plan}")
        _logger.info(f"Tipo de include_maintenance_plan: {type(include_maintenance_plan)}")
        _logger.info("=" * 80)
        
        # Retorna valores para o template
        return {
            'doc_ids': docids,
            'doc_model': 'engc.preventive.cronograma',
            'docs': cronogramas,  # ✅ Aqui que popula o 'docs' para o template!
            'data': data,  # ✅ Passa o data para o template também
        }
