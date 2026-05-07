"""Wrapper para chamadas ao daemon WireGuard no host."""

import logging

import requests
from odoo.exceptions import UserError

_log = logging.getLogger(__name__)


class WgRunner:
    def __init__(self, env):
        get = env['ir.config_parameter'].sudo().get_param
        self.daemon_url = (get('afr_iot_wireguard.daemon_url') or 'http://172.17.0.1:9999').rstrip('/')
        self.interface = get('afr_iot_wireguard.interface') or 'wg0'
        self._secret = get('afr_iot_wireguard.daemon_secret') or ''

    def _headers(self):
        h = {'Content-Type': 'application/json'}
        if self._secret:
            h['X-Secret'] = self._secret
        return h

    def _post(self, path, payload):
        url = f'{self.daemon_url}{path}'
        try:
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=5)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            raise UserError(f'Timeout ao contactar daemon WireGuard ({url}).')
        except requests.exceptions.ConnectionError:
            raise UserError(f'Não foi possível conectar ao daemon WireGuard ({url}).')
        except requests.exceptions.HTTPError as e:
            body = {}
            try:
                body = e.response.json()
            except Exception:
                pass
            raise UserError(f'Daemon retornou erro: {body.get("error", str(e))}')

    def add_peer(self, public_key: str, assigned_ip: str):
        """Register a new peer on the WireGuard interface."""
        result = self._post('/peer/add', {
            'interface': self.interface,
            'public_key': public_key,
            'allowed_ips': f'{assigned_ip}/32',
        })
        _log.info('Peer adicionado: %s... → %s', public_key[:8], assigned_ip)
        return result

    def remove_peer(self, public_key: str):
        """Remove a peer from the WireGuard interface."""
        result = self._post('/peer/remove', {
            'interface': self.interface,
            'public_key': public_key,
        })
        _log.info('Peer removido: %s...', public_key[:8])
        return result

    def health(self):
        """Check daemon connectivity."""
        try:
            resp = requests.get(f'{self.daemon_url}/health', timeout=3)
            return resp.status_code == 200
        except Exception:
            return False
