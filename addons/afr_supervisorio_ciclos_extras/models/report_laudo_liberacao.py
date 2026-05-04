# -*- coding: utf-8 -*-
"""Modelo abstrato para processar dados do Laudo de Liberação"""
from odoo import models, api
import logging
import qrcode
from io import BytesIO
import base64

_logger = logging.getLogger(__name__)


class ReportLaudoLiberacao(models.AbstractModel):
    """
    Modelo abstrato para o relatório de Laudo de Liberação.
    
    Processa os dados antes de enviar para o template QWeb.
    """
    _name = 'report.afr_supervisorio_ciclos_extras.report_laudo_liberacao_template'
    _description = 'Relatório de Laudo de Liberação de Produtos'
    _table = 'report_laudo_liberacao'  # Nome curto para evitar erro de tabela muito longa (limite PostgreSQL: 63 caracteres)

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Retorna os valores para o template do relatório.
        
        Args:
            docids: Lista de IDs dos ciclos de esterilização
            data: Dicionário com material_line_ids (IDs dos materiais selecionados)
        
        Returns:
            dict: Dicionário com 'docs', 'data' e outros valores para o template
        """
        data = data or {}
        
        # Se docids estiver vazio, tenta pegar do contexto (active_ids)
        if not docids:
            active_ids = self.env.context.get('active_ids', [])
            if active_ids:
                docids = active_ids
        
        # Busca os ciclos
        ciclos = self.env['afr.supervisorio.ciclos'].browse(docids) if docids else self.env['afr.supervisorio.ciclos']
        
        # Busca os materiais selecionados (filtrados pelo wizard)
        # Se não houver material_line_ids no data, mostra todos os materiais dos ciclos
        material_line_ids = data.get('material_line_ids', [])
        if material_line_ids:
            # Filtro aplicado pelo wizard - usa apenas os materiais selecionados
            material_lines = self.env['afr.supervisorio.cycle.materials.lines'].browse(material_line_ids)
        else:
            # Sem filtro (rota pública) - mostra todos os materiais de todos os ciclos
            material_lines = self.env['afr.supervisorio.cycle.materials.lines']
            for ciclo in ciclos:
                material_lines |= ciclo.material_lines_ids
        
        # Gera QR code e link curto para cada ciclo (verificação de autenticidade)
        ShortLink = self.env['afr.laudo.short.link']
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        qr_codes = {}
        short_urls = {}
        for ciclo in ciclos:
            try:
                selected_ids = material_lines.filtered(lambda l: l.ciclo_id.id == ciclo.id).ids
                if not selected_ids:
                    qr_codes[ciclo.id] = None
                    short_urls[ciclo.id] = None
                    continue

                # Obtém ou cria link curto; QR code e relatório usam a URL curta
                short_link = ShortLink.get_or_create_short_link(ciclo.id, selected_ids)
                short_url = f"{base_url}/v/{short_link.short_code}"
                qr_buffer = BytesIO()
                qrcode.make(short_url.encode(), box_size=4).save(qr_buffer, optimise=True, format='PNG')
                img_str = base64.b64encode(qr_buffer.getvalue()).decode()
                qr_codes[ciclo.id] = img_str
                short_urls[ciclo.id] = short_url
            except Exception as e:
                _logger.error(f"Erro ao gerar QR code/link curto para ciclo {ciclo.id}: {str(e)}")
                qr_codes[ciclo.id] = None
                short_urls[ciclo.id] = None

        # Assinatura: vinda do wizard (data) ou, em acesso público, sem assinatura
        signature_image_b64 = data.get('signature_image_b64')
        if data.get('signature_type') == 'auto' and not signature_image_b64:
            company = self.env.company
            if company and company.laudo_signature_default:
                raw = company.laudo_signature_default
                signature_image_b64 = base64.b64encode(raw).decode('utf-8') if isinstance(raw, bytes) else raw
        signer_name = data.get('signer_name') or ''
        signer_title = data.get('signer_title') or 'Garantia de qualidade'
        signature_date = data.get('signature_date')
        data_emissao = data.get('data_emissao')
        data_liberacao = data.get('data_liberacao')

        return {
            'doc_ids': docids,
            'doc_model': 'afr.supervisorio.ciclos',
            'docs': ciclos,
            'data': data,
            'material_lines_filtered': material_lines,
            'qr_codes': qr_codes,
            'short_urls': short_urls,
            'signature_image_b64': signature_image_b64,
            'signer_name': signer_name,
            'signer_title': signer_title,
            'signature_date': signature_date,
            'data_emissao': data_emissao,
            'data_liberacao': data_liberacao,
        }

