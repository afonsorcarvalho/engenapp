# -*- coding: utf-8 -*-
"""Mensagens individuais de uma sessão de chat com o LLM."""

from odoo import fields, models


class AfrLlmChatMessage(models.Model):
    _name = 'afr.llm.chat.message'
    _description = 'Mensagem do assistente LLM'
    _order = 'create_date asc, id asc'

    session_id = fields.Many2one(
        'afr.llm.chat.session',
        string='Sessão',
        required=True,
        ondelete='cascade',
        index=True,
    )
    role = fields.Selection(
        [
            ('user', 'Usuário'),
            ('assistant', 'Assistente'),
            ('system', 'Sistema'),
        ],
        string='Papel',
        required=True,
    )
    body = fields.Text(string='Conteúdo', required=True)
