"""Página de ativação de dispositivo — escaneada pelo admin via QR code."""

import logging

from odoo import http
from odoo.http import request
from odoo.exceptions import UserError

from ..services.ip_allocator import allocate_ip
from ..services.wg_runner import WgRunner

_log = logging.getLogger(__name__)

_GROUP_APPROVER = 'afr_iot_wireguard.group_approver'


class WireguardActivateController(http.Controller):

    @http.route('/activate', type='http', auth='user', csrf=True, methods=['GET', 'POST'], sitemap=False)
    def activate(self, code=None, **_kwargs):
        if not request.env.user.has_group(_GROUP_APPROVER):
            return request.render('afr_iot_wireguard.activate_error_template', {
                'message': 'Você não tem permissão para ativar dispositivos WireGuard.',
            })

        if not code:
            return request.render('afr_iot_wireguard.activate_error_template', {
                'message': 'Código de ativação não informado.',
            })

        enrollment, status = request.env['wireguard.enrollment'].sudo().find_by_code(code)

        if status == 'not_found':
            return request.render('afr_iot_wireguard.activate_error_template', {
                'message': 'Código de ativação não encontrado.',
            })
        if status in ('expired', 'cancelled'):
            return request.render('afr_iot_wireguard.activate_error_template', {
                'message': 'Este código já expirou ou foi cancelado.',
            })
        if status == 'activated':
            return request.render('afr_iot_wireguard.activate_error_template', {
                'message': 'Este dispositivo já foi ativado.',
            })

        device = enrollment.device_id

        if request.httprequest.method == 'GET':
            return request.render('afr_iot_wireguard.activate_template', {
                'enrollment': enrollment,
                'device': device,
            })

        # POST — perform activation
        action = request.params.get('action', '')

        if action == 'cancel':
            enrollment.sudo().write({'state': 'cancelled'})
            return request.render('afr_iot_wireguard.activate_success_template', {
                'message': 'Ativação cancelada.',
                'success': False,
                'device': device,
            })

        if device.state == 'active':
            return request.render('afr_iot_wireguard.activate_error_template', {
                'message': 'Este dispositivo já foi ativado.',
            })

        try:
            assigned_ip = allocate_ip(request.env)
            runner = WgRunner(request.env)
            runner.add_peer(device.public_key, assigned_ip)
            device.sudo().activate(enrollment, assigned_ip)
            return request.render('afr_iot_wireguard.activate_success_template', {
                'message': f'Dispositivo ativado com sucesso! IP: {assigned_ip}',
                'success': True,
                'device': device,
            })
        except UserError as e:
            _log.error('Erro ao ativar dispositivo %s: %s', device.device_hw_id, e)
            return request.render('afr_iot_wireguard.activate_error_template', {
                'message': str(e.args[0]),
            })
        except Exception as e:
            _log.exception('Erro inesperado ao ativar dispositivo %s', device.device_hw_id)
            return request.render('afr_iot_wireguard.activate_error_template', {
                'message': 'Erro interno ao ativar o dispositivo. Verifique os logs.',
            })
