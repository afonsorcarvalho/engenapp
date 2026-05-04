# -*- coding: utf-8 -*-
"""
Modelo para armazenar links curtos de verificação de autenticidade do laudo.

Cada registro mapeia um código curto (ex.: /v/Ab3xY2) para um ciclo e lista de
materiais, permitindo que o QR code e o relatório exibam um link curto em vez
da URL completa com token e parâmetros.
"""
import secrets
from odoo import models, fields, api


class LaudoShortLink(models.Model):
    _name = 'afr.laudo.short.link'
    _description = 'Link curto para verificação de autenticidade do laudo'

    short_code = fields.Char(
        string='Código curto',
        required=True,
        index=True,
        copy=False,
        help='Código usado na URL curta (ex.: /v/Ab3xY2)',
    )
    ciclo_id = fields.Many2one(
        'afr.supervisorio.ciclos',
        string='Ciclo',
        required=True,
        ondelete='cascade',
    )
    material_line_ids_str = fields.Char(
        string='IDs dos materiais (CSV)',
        required=True,
        help='Lista de IDs de afr.supervisorio.cycle.materials.lines separados por vírgula',
    )

    _sql_constraints = [
        ('short_code_unique', 'UNIQUE(short_code)', 'O código curto já existe.'),
    ]

    @api.model
    def _generate_short_code(self):
        """Gera um código curto URL-safe único (aprox. 8 caracteres)."""
        for _ in range(20):
            code = secrets.token_urlsafe(6)
            if not self.search_count([('short_code', '=', code)]):
                return code
        raise ValueError('Não foi possível gerar código curto único.')

    @api.model
    def get_or_create_short_link(self, ciclo_id, material_line_ids):
        """
        Retorna um registro de link curto para o ciclo e materiais dados.
        Se já existir um com o mesmo ciclo e mesma lista de materiais, reutiliza;
        caso contrário, cria um novo.

        Args:
            ciclo_id: int, ID do ciclo (afr.supervisorio.ciclos).
            material_line_ids: list[int], IDs das linhas de materiais.

        Returns:
            afr.laudo.short.link: registro do link curto.
        """
        material_line_ids = sorted(set(int(x) for x in material_line_ids))
        materials_str = ','.join(str(x) for x in material_line_ids)
        existing = self.search([
            ('ciclo_id', '=', ciclo_id),
            ('material_line_ids_str', '=', materials_str),
        ], limit=1)
        if existing:
            return existing
        code = self._generate_short_code()
        return self.create({
            'short_code': code,
            'ciclo_id': ciclo_id,
            'material_line_ids_str': materials_str,
        })

    def get_full_url(self):
        """
        Monta a URL completa de download do laudo (com token e materials)
        para uso no redirect do controller.

        Returns:
            str: URL absoluta para download do PDF.
        """
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        ciclo = self.ciclo_id
        material_line_ids = [int(x) for x in self.material_line_ids_str.split(',') if x.strip()]
        token = ciclo._get_laudo_public_token(material_line_ids=material_line_ids)
        materials_param = self.material_line_ids_str
        return f"{base_url}/laudo/liberacao/public/{ciclo.id}?token={token}&materials={materials_param}"
