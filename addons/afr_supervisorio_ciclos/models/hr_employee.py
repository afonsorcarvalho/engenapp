# -*- coding: utf-8 -*-
"""
Extensão de hr.employee: dados usados na assinatura de relatórios de ciclo.

Os campos abaixo são a fonte única de verdade para documentação profissional,
conselho, número de registro, CPF e imagem da assinatura exibidos no PDF.
"""
from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    afr_professional_documentation = fields.Char(
        string='Documentação profissional',
        help='Texto para registro/documentação profissional exibido na assinatura do ciclo.',
    )
    afr_professional_council = fields.Char(
        string='Conselho de profissão',
        help='Sigla ou nome do conselho (ex.: COREN, CRM, CRF).',
    )
    afr_professional_council_number = fields.Char(
        string='Número no conselho',
    )
    afr_professional_cpf = fields.Char(
        string='CPF (para assinatura de ciclo)',
        help='CPF exibido na identificação da assinatura nos relatórios de ciclo.',
    )
    # Armazena PNG (base64) gerado pelo widget nativo `signature` (web.SignatureField):
    # diálogo com modos Auto / Draw / Load — ver web/static/src/core/signature/name_and_signature.xml
    afr_signature_image = fields.Binary(
        string='Assinatura digital',
        attachment=True,
        help='Assinatura para relatórios de ciclo: no formulário use o widget para Auto (nome), '
             'Draw (à mão livre) ou Load (imagem).',
    )
