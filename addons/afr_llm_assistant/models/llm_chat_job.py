# -*- coding: utf-8 -*-
"""
Fila leve para processar o assistente LLM sem bloquear o primeiro RPC.

O fluxo é: ``action_queue_message`` na sessão (rápido) → ``action_process`` no job
(processamento longo). O cliente deve chamar ``action_process`` com
``orm.silent`` para não acionar o indicador global de RPC do Odoo.
"""

import logging

from odoo import fields, models, _
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class AfrLlmChatJob(models.Model):
    _name = 'afr.llm.chat.job'
    _description = 'Job de processamento do assistente LLM'
    _order = 'id desc'

    session_id = fields.Many2one(
        'afr.llm.chat.session',
        string='Sessão',
        required=True,
        ondelete='cascade',
        index=True,
    )
    state = fields.Selection(
        [
            ('pending', 'Pendente'),
            ('processing', 'Em processamento'),
            ('done', 'Concluído'),
            ('error', 'Erro'),
        ],
        string='Estado',
        default='pending',
        required=True,
        index=True,
    )
    error_message = fields.Text(string='Mensagem de erro')

    def action_process(self):
        """
        Executa o pipeline LLM para a sessão (mensagem do utilizador já gravada).

        Apenas um pedido com sucesso passa de ``pending`` a ``processing`` (SQL atómico).
        """
        self.ensure_one()
        if self.session_id.user_id.id != self.env.user.id:
            raise AccessError(_('Este job não lhe pertence.'))
        if self.state != 'pending':
            return {'state': self.state, 'skipped': True}

        self.env.cr.execute(
            """
            UPDATE afr_llm_chat_job
               SET state = 'processing'
             WHERE id = %s
               AND state = 'pending'
            """,
            (self.id,),
        )
        if self.env.cr.rowcount == 0:
            self.invalidate_recordset()
            return {'state': self.state, 'skipped': True}

        self.invalidate_recordset()
        try:
            body = self.session_id._compose_llm_response_text()
            self.env['afr.llm.chat.message'].create({
                'session_id': self.session_id.id,
                'role': 'assistant',
                'body': body,
            })
            self.write({'state': 'done', 'error_message': False})
        except Exception as err:
            # Não relançar: o RPC longo é chamado com orm.silent; o cliente lê estado/mensagens.
            msg = str(err)
            _logger.exception('Job LLM falhou (sessão %s)', self.session_id.id)
            self.write({'state': 'error', 'error_message': msg})
            self.env['afr.llm.chat.message'].create({
                'session_id': self.session_id.id,
                'role': 'assistant',
                'body': _('(Erro ao gerar resposta) %s') % msg,
            })
            return {'state': 'error', 'skipped': False, 'message': msg}
        return {'state': 'done', 'skipped': False}
