# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class WizardLerDiretorioCiclos(models.TransientModel):
    """
    Wizard para configurar o range de datas para leitura do diretório de ciclos.
    
    Este wizard permite ao usuário definir um período específico para a leitura
    dos arquivos de ciclos de esterilização, lavagem e desinfecção.
    """
    _name = 'wizard.ler.diretorio.ciclos'
    _description = 'Wizard para Leitura de Diretório de Ciclos'

    # Campos de data
    data_inicio = fields.Date(
        string='Data Início',
        required=True,
        default=lambda self: datetime.now() - timedelta(days=30),
        help='Data inicial para a leitura dos ciclos'
    )
    
    data_fim = fields.Date(
        string='Data Fim',
        required=True,
        default=fields.Date.today,
        help='Data final para a leitura dos ciclos'
    )
    
        # Campo para o equipamento (opcional, pode ser usado para filtrar)
    equipment_id = fields.Many2one(
        'engc.equipment',
        string='Equipamento',
        domain="[('cycle_type_id', '!=', False)]",
        help='Equipamento específico para leitura (opcional)'
    )
    
    # Campo para mostrar informações sobre o range selecionado
    info_range = fields.Char(
        string='Período Selecionado',
        compute='_compute_info_range',
        store=False,
        help='Informações sobre o período selecionado'
    )

    @api.depends('data_inicio', 'data_fim')
    def _compute_info_range(self):
        """
        Calcula e exibe informações sobre o período selecionado.
        """
        for record in self:
            if record.data_inicio and record.data_fim:
                dias = (record.data_fim - record.data_inicio).days + 1
                record.info_range = f"Período: {record.data_inicio} a {record.data_fim} ({dias} dias)"
            else:
                record.info_range = ""

    @api.constrains('data_inicio', 'data_fim')
    def _check_dates(self):
        """
        Valida se as datas estão corretas.
        """
        for record in self:
            if record.data_inicio and record.data_fim:
                if record.data_inicio > record.data_fim:
                    raise ValidationError('A data de início não pode ser posterior à data de fim.')
                
                # Verifica se o período não é muito longo (opcional)
                # dias = (record.data_fim - record.data_inicio).days
                # if dias > 365:
                #     raise ValidationError('O período não pode ser superior a 365 dias.')

    def action_confirmar_leitura(self):
        """
        Executa a leitura do diretório com as datas configuradas.
        """
        self.ensure_one()
        
        # Converte as datas para datetime para compatibilidade com o método existente
        data_inicio_datetime = datetime.combine(self.data_inicio, datetime.min.time())
        data_fim_datetime = datetime.combine(self.data_fim, datetime.max.time())
        
        try:
            # Obtém o contexto do registro atual (se houver)
            active_model = self.env.context.get('active_model')
            active_id = self.env.context.get('active_id')
            
            if active_model == 'afr.supervisorio.ciclos' and active_id:
                # Se foi chamado de um registro específico, usa esse equipamento
                ciclo = self.env[active_model].browse(active_id)
                equipment_id = ciclo.equipment_id
            else:
                # Usa o equipamento selecionado no wizard ou busca o primeiro disponível
                equipment_id = self.equipment_id
               
                    
                if not equipment_id:
                    raise UserError('Nenhum equipamento encontrado com tipo de ciclo definido.')
            
            # Chama o método de leitura do diretório com as datas configuradas
            ciclo_model = self.env['afr.supervisorio.ciclos']
            ciclo_model.action_ler_diretorio_ciclos(
                equipment_id=equipment_id,
                data_inicial=data_inicio_datetime,
                data_final=data_fim_datetime
            )
            
            # Retorna uma mensagem de sucesso
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sucesso!',
                    'message': f'Leitura do diretório concluída com sucesso para o período de {self.data_inicio} a {self.data_fim}.',
                    'type': 'success',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            _logger.error(f"Erro na leitura do diretório: {str(e)}")
            raise UserError(f'Erro na leitura do diretório: {str(e)}')

    def action_cancelar(self):
        """
        Cancela o wizard e fecha a janela.
        """
        return {'type': 'ir.actions.act_window_close'}
