# -*- coding: utf-8 -*-
"""
Estende res.users para suporte a FCM (Firebase Cloud Messaging).
O app Flutter chama register_fcm_token via RPC após o login.
"""
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    fcm_token = fields.Char(
        string='Token FCM',
        index=True,
        copy=False,
        help='Token do dispositivo para Firebase Cloud Messaging. '
             'Registrado pelo app mobile via RPC (register_fcm_token) após o login.'
    )

    def register_fcm_token(self, token):
        """
        Registra o token FCM do dispositivo para o usuário atual.
        Chamado via RPC pelo app Flutter após o login, com args = [[uid], token].

        :param token: string com o token FCM do dispositivo (ou False/None para limpar)
        :return: True em caso de sucesso
        """
        self.ensure_one()
        self.write({'fcm_token': token or False})
        _logger.debug("FCM token registrado para o usuário %s (ID %s).", self.login, self.id)
        return True
