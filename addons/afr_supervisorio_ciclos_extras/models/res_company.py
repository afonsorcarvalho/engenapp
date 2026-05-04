# -*- coding: utf-8 -*-
"""
Extensão de res.company para assinatura padrão do laudo de liberação.

Permite configurar uma assinatura e dados do signatário por empresa,
usada quando o wizard escolhe "Assinatura automática".
"""
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Assinatura padrão para laudo (usada quando tipo = automática)
    laudo_signature_default = fields.Binary(
        string='Assinatura padrão (Laudo)',
        attachment=False,
        help='Imagem PNG da assinatura usada quando o laudo é gerado com assinatura automática.',
    )
    laudo_signer_name_default = fields.Char(
        string='Nome do responsável (padrão)',
        help='Nome exibido no laudo quando se usa assinatura automática.',
    )
    laudo_signer_title_default = fields.Char(
        string='Cargo/função (padrão)',
        default='Garantia de qualidade',
        help='Cargo ou função exibido no laudo (ex.: Garantia de qualidade, Responsável técnico).',
    )
