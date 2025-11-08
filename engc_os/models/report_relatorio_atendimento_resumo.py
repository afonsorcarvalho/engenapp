# -*- coding: utf-8 -*-

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class ReportRelatorioAtendimentoResumo(models.AbstractModel):
    """
    Modelo abstrato para o relatório resumido de atendimentos.
    
    Disponibiliza os dados de filtro no template.
    """
    _name = 'report.engc_os.report_relatorio_atendimento_resumo_template'
    _description = 'Relatório Resumido de Atendimentos'

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Retorna os valores para o template do relatório.
        
        Args:
            docids: Lista de IDs dos relatórios de atendimento
            data: Dicionário com os dados de filtro (equipment_id, date_start, date_end, state)
        
        Returns:
            dict: Dicionário com os valores disponíveis no template
        """
        data = data or {}
        
        _logger.debug("="*50)
        _logger.debug("_get_report_values chamado")
        _logger.debug("docids recebido: %s (tipo: %s)", docids, type(docids))
        _logger.debug("data: %s", data)
        _logger.debug("context: %s", self.env.context)
        
        # Se docids estiver vazio, tenta pegar do contexto (active_ids)
        if not docids:
            active_ids = self.env.context.get('active_ids', [])
            _logger.debug("docids vazio, tentando usar active_ids do contexto: %s", active_ids)
            if active_ids:
                docids = active_ids
            else:
                # Tenta pegar do data se disponível
                if isinstance(data, dict) and 'context' in data:
                    active_ids = data['context'].get('active_ids', [])
                    _logger.debug("Tentando pegar active_ids do data['context']: %s", active_ids)
                    if active_ids:
                        docids = active_ids
        
        _logger.debug("docids final a ser usado: %s", docids)
        
        # Busca os relatórios
        relatorios = self.env['engc.os.relatorios'].browse(docids) if docids else self.env['engc.os.relatorios']
        
        _logger.debug("Relatórios carregados: %d", len(relatorios))
        _logger.debug("IDs dos relatórios: %s", relatorios.ids)
        if relatorios:
            _logger.debug("Nomes dos relatórios: %s", [r.name for r in relatorios[:5]])
        _logger.debug("="*50)
        
        # Agrupa os relatórios por equipamento e depois por OS
        grouped_data = {}
        equipment_summaries = {}
        total_summary = {
            'draft': 0,
            'done': 0,
            'cancel': 0,
            'total_time': 0.0,
            'total_count': 0
        }
        
        for relatorio in relatorios:
            # Obtém o equipamento (usa o campo related equipment_id)
            equipment = relatorio.equipment_id or (relatorio.os_id.equipment_id if relatorio.os_id else False)
            equipment_id = equipment.id if equipment else False
            equipment_name = equipment.name if equipment else 'Sem Equipamento'
            
            # Obtém a OS (pode ser None)
            os_id = relatorio.os_id.id if relatorio.os_id else False
            os_name = relatorio.os_id.name if relatorio.os_id else 'Sem OS'
            
            # Inicializa estrutura para o equipamento se não existir
            if equipment_id not in grouped_data:
                grouped_data[equipment_id] = {
                    'equipment_id': equipment_id,
                    'equipment_name': equipment_name,
                    'os_groups': {},
                    'summary': {
                        'draft': 0,
                        'done': 0,
                        'cancel': 0,
                        'total_time': 0.0,
                        'total_count': 0
                    },
                    'os_summary': {
                        'draft': 0,
                        'under_budget': 0,
                        'pause_budget': 0,
                        'wait_authorization': 0,
                        'wait_parts': 0,
                        'execution_ready': 0,
                        'under_repair': 0,
                        'pause_repair': 0,
                        'reproved': 0,
                        'done': 0,
                        'cancel': 0,
                        'total_os_count': 0
                    }
                }
            
            # Inicializa estrutura para a OS se não existir
            if os_id not in grouped_data[equipment_id]['os_groups']:
                os_record = relatorio.os_id
                # Coleta informações da OS
                # Formata a data de requisição
                date_request_formatted = False
                if os_record and os_record.date_request:
                    date_request_formatted = os_record.date_request.strftime('%d/%m/%Y %H:%M')
                
                os_state = os_record.state if os_record else False
                
                # Atualiza resumo de OSs por status
                if os_state and os_state in grouped_data[equipment_id]['os_summary']:
                    grouped_data[equipment_id]['os_summary'][os_state] += 1
                    grouped_data[equipment_id]['os_summary']['total_os_count'] += 1
                
                os_info = {
                    'os_id': os_id,
                    'os_name': os_name,
                    'solicitante': os_record.solicitante if os_record else '',
                    'problem_description': os_record.problem_description if os_record else '',
                    'date_request': os_record.date_request if os_record and os_record.date_request else False,
                    'date_request_formatted': date_request_formatted,
                    'maintenance_type': os_record.maintenance_type if os_record else False,
                    'maintenance_type_label': self._get_maintenance_type_label(os_record.maintenance_type) if os_record else '',
                    'os_state': os_state,
                    'os_state_label': self._get_os_state_label(os_state) if os_state else '',
                    'time_execution': os_record.relatorios_time_execution if os_record else 0.0,
                    'request_parts': [],  # Peças requisitadas
                    'applied_parts': [],  # Peças aplicadas
                    'relatorios': []
                }
                
                # Coleta informações de peças requisitadas e aplicadas
                if os_record and os_record.request_parts:
                    for part in os_record.request_parts:
                        part_info = {
                            'product_name': part.product_id.name if part.product_id else '',
                            'product_code': part.product_id.default_code if part.product_id and part.product_id.default_code else '',
                            'quantity': part.product_uom_qty or 0.0,
                            'uom': part.product_uom.name if part.product_uom else '',
                            'state': part.state if part.state else '',
                            'state_label': self._get_part_state_label(part.state) if part.state else ''
                        }
                        
                        # Adiciona às peças requisitadas
                        os_info['request_parts'].append(part_info)
                        
                        # Se aplicada, adiciona também às peças aplicadas
                        if part.state == 'aplicada':
                            os_info['applied_parts'].append(part_info)
                
                grouped_data[equipment_id]['os_groups'][os_id] = os_info
            
            # Adiciona informações detalhadas do relatório
            relatorio_info = {
                'relatorio': relatorio,
                'fault_description': relatorio.fault_description if relatorio.fault_description else '',
                'service_summary': relatorio.service_summary if relatorio.service_summary else '',
                'pendency': relatorio.pendency if relatorio.pendency else '',
                'state_equipment': relatorio.state_equipment if relatorio.state_equipment else False,
                'state_equipment_label': self._get_equipment_state_label(relatorio.state_equipment) if relatorio.state_equipment else ''
            }
            
            # Adiciona o relatório ao grupo da OS
            grouped_data[equipment_id]['os_groups'][os_id]['relatorios'].append(relatorio_info)
            
            # Atualiza resumo do equipamento
            state = relatorio.state or 'draft'
            if state in ['draft', 'done', 'cancel']:
                grouped_data[equipment_id]['summary'][state] += 1
            grouped_data[equipment_id]['summary']['total_time'] += relatorio.time_execution or 0.0
            grouped_data[equipment_id]['summary']['total_count'] += 1
            
            # Atualiza resumo geral
            if state in ['draft', 'done', 'cancel']:
                total_summary[state] += 1
            total_summary['total_time'] += relatorio.time_execution or 0.0
            total_summary['total_count'] += 1
        
        # Calcula disponibilidade por equipamento
        # Primeiro, coleta todos os relatórios por equipamento ordenados por data
        from datetime import datetime, timedelta
        
        equipment_relatorios_ordered = {}
        for relatorio in relatorios:
            equipment = relatorio.equipment_id or (relatorio.os_id.equipment_id if relatorio.os_id else False)
            equipment_id = equipment.id if equipment else False
            
            if equipment_id:
                if equipment_id not in equipment_relatorios_ordered:
                    equipment_relatorios_ordered[equipment_id] = []
                equipment_relatorios_ordered[equipment_id].append(relatorio)
        
        # Ordena os relatórios por data de fim de atendimento para cada equipamento
        for equipment_id in equipment_relatorios_ordered:
            equipment_relatorios_ordered[equipment_id].sort(
                key=lambda r: r.data_fim_atendimento if r.data_fim_atendimento else datetime.min
            )
        
        # Calcula tempo parado e disponibilidade para cada equipamento
        date_start = None
        date_end = None
        if data.get('date_start'):
            try:
                if isinstance(data['date_start'], str):
                    date_start = datetime.strptime(data['date_start'], '%d/%m/%Y %H:%M')
                else:
                    date_start = data['date_start']
            except:
                pass
        if data.get('date_end'):
            try:
                if isinstance(data['date_end'], str):
                    date_end = datetime.strptime(data['date_end'], '%d/%m/%Y %H:%M')
                else:
                    date_end = data['date_end']
            except:
                pass
        
        # Se não tiver datas no data, tenta pegar do contexto ou usar as datas dos relatórios
        if not date_start or not date_end:
            if relatorios:
                dates = [r.data_atendimento for r in relatorios if r.data_atendimento]
                if dates:
                    date_start = date_start or min(dates)
                    date_end = date_end or max([r.data_fim_atendimento for r in relatorios if r.data_fim_atendimento] or dates)
        
        # Calcula disponibilidade por equipamento
        for equipment_id in grouped_data:
            equipment_group = grouped_data[equipment_id]
            total_maintenance_time = equipment_group['summary']['total_time']  # Tempo de manutenção
            total_downtime = 0.0  # Tempo parado
            
            # Calcula tempo parado baseado no estado do equipamento
            if equipment_id in equipment_relatorios_ordered:
                relatorios_eq = equipment_relatorios_ordered[equipment_id]
                
                for i, relatorio in enumerate(relatorios_eq):
                    # Se o relatório terminou com equipamento parado
                    if relatorio.state_equipment == 'parado' and relatorio.data_fim_atendimento:
                        # Procura o próximo relatório onde o equipamento ficou funcionando
                        downtime_end = None
                        
                        # Verifica se há próximo relatório
                        for j in range(i + 1, len(relatorios_eq)):
                            next_relatorio = relatorios_eq[j]
                            if next_relatorio.state_equipment == 'funcionando' and next_relatorio.data_atendimento:
                                downtime_end = next_relatorio.data_atendimento
                                break
                        
                        # Se não encontrou próximo relatório funcionando, usa a data fim do período
                        if not downtime_end:
                            downtime_end = date_end if date_end else relatorio.data_fim_atendimento
                        
                        # Calcula o tempo parado em horas
                        if downtime_end and relatorio.data_fim_atendimento:
                            delta = downtime_end - relatorio.data_fim_atendimento
                            total_downtime += delta.total_seconds() / 3600.0
            
            # Tempo total indisponível = manutenção + parado
            total_unavailable_time = total_maintenance_time + total_downtime
            
            # Calcula período total em horas
            period_total_hours = 0.0
            if date_start and date_end:
                delta = date_end - date_start
                period_total_hours = delta.total_seconds() / 3600.0
            
            # Calcula disponibilidade (em porcentagem)
            availability_percent = 0.0
            if period_total_hours > 0:
                available_time = period_total_hours - total_unavailable_time
                availability_percent = (available_time / period_total_hours) * 100.0
                if availability_percent < 0:
                    availability_percent = 0.0
                if availability_percent > 100:
                    availability_percent = 100.0
            
            # Adiciona ao resumo do equipamento
            equipment_group['summary']['total_maintenance_time'] = total_maintenance_time
            equipment_group['summary']['total_downtime'] = total_downtime
            equipment_group['summary']['total_unavailable_time'] = total_unavailable_time
            equipment_group['summary']['period_total_hours'] = period_total_hours
            equipment_group['summary']['availability_percent'] = availability_percent
        
        # Converte o dicionário agrupado em lista ordenada (por nome do equipamento)
        grouped_list = []
        equipment_parts_summary = {}  # Resumo de peças aplicadas por equipamento
        
        for equipment_id in sorted(grouped_data.keys(), key=lambda x: grouped_data[x]['equipment_name']):
            equipment_group = grouped_data[equipment_id]
            # Ordena as OSs por nome dentro de cada equipamento
            os_list = []
            equipment_applied_parts = {}  # Agrupa peças aplicadas por equipamento
            
            for os_id in sorted(equipment_group['os_groups'].keys(), 
                              key=lambda x: equipment_group['os_groups'][x]['os_name']):
                os_info = equipment_group['os_groups'][os_id]
                os_list.append(os_info)
                
                # Agrupa peças aplicadas por equipamento
                for part in os_info.get('applied_parts', []):
                    part_key = part.get('product_code') or part.get('product_name', '')
                    if part_key:
                        if part_key not in equipment_applied_parts:
                            equipment_applied_parts[part_key] = {
                                'product_name': part.get('product_name', ''),
                                'product_code': part.get('product_code', ''),
                                'total_quantity': 0.0,
                                'uom': part.get('uom', '')
                            }
                        equipment_applied_parts[part_key]['total_quantity'] += part.get('quantity', 0.0)
            
            equipment_group['os_list'] = os_list
            equipment_group['applied_parts_summary'] = list(equipment_applied_parts.values())
            equipment_parts_summary[equipment_id] = equipment_applied_parts
            grouped_list.append(equipment_group)
        
        # Retorna os valores para o template
        result = {
            'doc_ids': docids or [],
            'doc_model': 'engc.os.relatorios',
            'docs': relatorios,  # Mantém para compatibilidade
            'grouped_data': grouped_list,  # Dados agrupados por equipamento e OS
            'total_summary': total_summary,  # Resumo geral
            'equipment_parts_summary': equipment_parts_summary,  # Resumo de peças por equipamento
            'data': data,  # Disponibiliza os dados de filtro como 'data'
            'options': data,  # Também disponibiliza como 'options' para compatibilidade
        }
        
        _logger.debug("Valores retornados: doc_ids=%s, docs=%d registros, equipamentos=%d", 
                     docids, len(relatorios), len(grouped_list))
        
        return result
    
    def _get_maintenance_type_label(self, maintenance_type):
        """Retorna o label do tipo de manutenção."""
        labels = {
            'corrective': 'Corretiva',
            'preventive': 'Preventiva',
            'instalacao': 'Instalação',
            'treinamento': 'Treinamento',
            'preditiva': 'Preditiva',
            'qualification': 'Qualificação',
            'loan': 'Comodato',
            'calibration': 'Calibração',
        }
        return labels.get(maintenance_type, maintenance_type or '')
    
    def _get_os_state_label(self, state):
        """Retorna o label do status da OS."""
        labels = {
            'draft': 'Criada',
            'under_budget': 'Em Orçamento',
            'pause_budget': 'Orçamento Pausado',
            'wait_authorization': 'Esperando aprovação',
            'wait_parts': 'Esperando peças',
            'execution_ready': 'Pronta para Execução',
            'under_repair': 'Em execução',
            'pause_repair': 'Execução Pausada',
            'reproved': 'Reprovada',
            'done': 'Concluída',
            'cancel': 'Cancelada',
        }
        return labels.get(state, state or '')
    
    def _get_part_state_label(self, state):
        """Retorna o label do status da peça."""
        labels = {
            'requisitada': 'Requisitada',
            'autorizada': 'Autorizada',
            'aplicada': 'Aplicada',
            'nao_autorizada': 'Não Autorizada',
            'cancel': 'Cancelada',
        }
        return labels.get(state, state or '')
    
    def _get_equipment_state_label(self, state):
        """Retorna o label do estado do equipamento."""
        labels = {
            'parado': 'Parado',
            'funcionando': 'Funcionando',
            'restricao': 'Funcionando com restrições',
        }
        return labels.get(state, state or '')

