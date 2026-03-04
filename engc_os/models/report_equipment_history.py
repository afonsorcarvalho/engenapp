# -*- coding: utf-8 -*-

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class ReportEquipmentHistory(models.AbstractModel):
    """
    Modelo abstrato para o relatório de histórico de atendimentos do equipamento.

    Lista todos os relatórios de atendimento vinculados às ordens de serviço
    do equipamento, ordenados por data de atendimento decrescente.
    """

    _name = 'report.engc_os.report_equipment_history_template'
    _description = 'Relatório Histórico de Atendimentos do Equipamento'

    def _format_hours_to_hhmm(self, hours):
        """
        Converte horas decimais para formato hh:mm.

        Args:
            hours: Número de horas em formato decimal (ex: 2.5 = 2h30min)

        Returns:
            str: String no formato "hh:mm"
        """
        if hours is None or hours < 0:
            return "00:00"
        total_minutes = int(hours * 60)
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h:02d}:{m:02d}"

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Retorna os valores para o template do relatório de histórico do equipamento.

        Para cada equipamento em docids, coleta todos os relatórios de atendimento
        das suas ordens de serviço (excluindo cancelados), ordenados por data
        de atendimento decrescente.

        Args:
            docids: Lista de IDs dos equipamentos (engc.equipment)
            data: Dados adicionais (não utilizado)

        Returns:
            dict: doc_ids, doc_model, equipment, lines (lista de dicts por registro)
        """
        data = data or {}
        Equipment = self.env['engc.equipment'].browse(docids)
        lines_by_equipment = {}

        STATE_LABELS = {
            'requisitada': 'Requisitadas',
            'autorizada': 'Autorizadas',
            'aplicada': 'Aplicadas',
            'nao_autorizada': 'Não Autorizadas',
            'cancel': 'Canceladas',
        }
        RequestParts = self.env['engc.os.request.parts']

        for equipment in Equipment:
            # Relatórios de todas as OS do equipamento (flat), excluindo cancelados
            relatorios = self.env['engc.os.relatorios']
            for os_record in equipment.oses:
                relatorios |= os_record.relatorios_id.filtered(
                    lambda r: r.state != 'cancel'
                )
            # Ordenação por data de atendimento decrescente
            relatorios = relatorios.sorted(
                key=lambda r: r.data_atendimento or '',
                reverse=True
            )
            lines = []
            for rel in relatorios:
                time_fmt = self._format_hours_to_hhmm(rel.time_execution)
                date_fmt = (
                    rel.data_atendimento.strftime('%d/%m/%Y %H:%M')
                    if rel.data_atendimento else ''
                )
                # Peças vinculadas ao relatório (requisitadas ou aplicadas neste relatório)
                parts = RequestParts.search([
                    '|',
                    ('relatorio_request_id', '=', rel.id),
                    ('relatorio_application_id', '=', rel.id),
                ])
                # Agrupa por estado para exibir na célula Resumo do Atendimento
                parts_by_state = []
                for state_key in ('requisitada', 'autorizada', 'aplicada', 'nao_autorizada', 'cancel'):
                    state_parts = parts.filtered(lambda p, s=state_key: p.state == s)
                    if not state_parts:
                        continue
                    items = []
                    for p in state_parts:
                        name = p.product_id.name if p.product_id else ''
                        code = (p.product_id.default_code or '').strip()
                        qty = p.product_uom_qty or 0
                        uom = p.product_uom.name if p.product_uom else ''
                        desc = f"{code} - {name}" if code else name
                        items.append({
                            'desc': desc,
                            'qty': qty,
                            'uom': uom,
                        })
                    parts_by_state.append({
                        'label': STATE_LABELS.get(state_key, state_key),
                        'items': items,
                    })
                lines.append({
                    'name': rel.name or '',
                    'os_name': rel.os_id.name if rel.os_id else '',
                    'data_atendimento': date_fmt,
                    'time_execution': time_fmt,
                    'service_summary': (rel.service_summary or '').strip() or '—',
                    'parts_by_state': parts_by_state,
                })
            lines_by_equipment[equipment.id] = lines

        return {
            'doc_ids': docids,
            'doc_model': 'engc.equipment',
            'equipment': Equipment,
            'lines_by_equipment': lines_by_equipment,
            'data': data,
        }
