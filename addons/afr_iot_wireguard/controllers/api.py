"""REST API endpoints consumidos pelos dispositivos IoT."""

import ipaddress
import json
import re
import logging

from odoo import http
from odoo.http import Response

_log = logging.getLogger(__name__)

_HW_ID_RE = re.compile(r'^[0-9a-fA-F]{12}$')
_PUBKEY_RE = re.compile(r'^[A-Za-z0-9+/]{43}=$')


def _json_response(data, status=200):
    return Response(json.dumps(data), status=status, content_type='application/json')


class WireguardApiController(http.Controller):

    @http.route('/api/enroll', type='http', auth='none', csrf=False, methods=['POST'])
    def enroll(self, **_kwargs):
        try:
            data = json.loads(http.request.httprequest.data)
        except (ValueError, TypeError):
            return _json_response({'error': 'JSON inválido'}, 400)

        hw_id = data.get('device_id', '')
        public_key = data.get('public_key', '')

        if not _HW_ID_RE.match(hw_id):
            return _json_response({'error': 'device_id inválido (esperado: 12 chars hex)'}, 400)
        if not _PUBKEY_RE.match(public_key):
            return _json_response({'error': 'public_key inválido (esperado: Curve25519 base64)'}, 400)

        env = http.request.env
        request_ip = http.request.httprequest.remote_addr
        base_url = env['ir.config_parameter'].sudo().get_param('web.base.url', '')

        attempt_model = env['wireguard.enroll.attempt'].sudo()
        if not attempt_model.check_rate_limit(request_ip, hw_id):
            _log.warning('Rate limit exceeded: ip=%s, device_id=%s', request_ip, hw_id)
            return _json_response({'error': 'Demasiadas tentativas. Tente novamente mais tarde.'}, 429)
        attempt_model.record_attempt(request_ip, hw_id)

        device = env['wireguard.device'].sudo().find_or_create_by_hw_id(hw_id, public_key)
        enrollment = env['wireguard.enrollment'].sudo().create_for_device(
            device, base_url=base_url, request_ip=request_ip,
        )

        poll_url = f'{base_url}/api/enroll/status/{enrollment.code}'

        return _json_response({
            'activation_code': enrollment.code,
            'activation_url': enrollment.activation_url,
            'poll_url': poll_url,
        }, 201)

    @http.route('/api/enroll/status/<string:code>', type='http', auth='none', csrf=False, methods=['GET'])
    def enroll_status(self, code, **_kwargs):
        env = http.request.env
        enrollment, status = env['wireguard.enrollment'].sudo().find_by_code(code)

        if status == 'not_found':
            return _json_response({'error': 'Código não encontrado'}, 404)

        if status in ('expired', 'cancelled'):
            return _json_response({'error': 'Código expirado ou cancelado'}, 410)

        if status == 'pending':
            return Response(status=204)

        # activated — return WireGuard config
        device = enrollment.device_id
        get_param = env['ir.config_parameter'].sudo().get_param

        # Determine prefix length from pool CIDR
        prefix_len = 24
        pool = env['wireguard.ip_pool'].sudo().search([('active', '=', True)], limit=1)
        if pool:
            try:
                prefix_len = ipaddress.ip_network(pool.cidr, strict=False).prefixlen
            except ValueError:
                pass

        payload = {
            'address': f'{device.assigned_ip}/{prefix_len}',
            'server_public_key': get_param('afr_iot_wireguard.server_public_key', ''),
            'server_endpoint': get_param('afr_iot_wireguard.server_endpoint', ''),
            'allowed_ips': get_param('afr_iot_wireguard.client_allowed_ips', '0.0.0.0/0'),
            'dns': get_param('afr_iot_wireguard.dns', ''),
        }
        return _json_response(payload, 200)
