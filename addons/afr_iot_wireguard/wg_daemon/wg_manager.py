#!/usr/bin/env python3
"""Daemon WireGuard para o módulo Odoo IoT Enrollment.

Roda no HOST (fora do container), como root.
Recebe comandos HTTP do Odoo para adicionar/remover peers WireGuard.

Uso:
    sudo python3 wg_manager.py --interface wg0 --port 9999 --secret <chave>

Instale como serviço systemd via wg_manager.service.
"""

import argparse
import json
import logging
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
_log = logging.getLogger('wg_manager')

_INTERFACE = 'wg0'
_SECRET: Optional[str] = None


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f'Comando falhou: {cmd}')
    return result.stdout.strip()


class WgHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):  # noqa: D102
        _log.info(fmt, *args)

    def log_error(self, fmt, *args):  # noqa: D102
        _log.error(fmt, *args)

    def _send(self, status: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _authorized(self) -> bool:
        if not _SECRET:
            return True
        return self.headers.get('X-Secret') == _SECRET

    def _read_body(self) -> Optional[dict]:
        try:
            length = int(self.headers.get('Content-Length', 0))
            return json.loads(self.rfile.read(length))
        except Exception:
            return None

    # ------------------------------------------------------------------
    def do_GET(self):  # noqa: N802
        if self.path == '/health':
            self._send(200, {'status': 'ok', 'interface': _INTERFACE})
        elif self.path == '/pubkey':
            if not self._authorized():
                self._send(403, {'error': 'forbidden'})
                return
            try:
                pubkey = _run(['wg', 'show', _INTERFACE, 'public-key'])
                port = _run(['wg', 'show', _INTERFACE, 'listen-port'])
                self._send(200, {
                    'interface': _INTERFACE,
                    'public_key': pubkey,
                    'listen_port': int(port) if port.isdigit() else port,
                })
            except Exception as e:
                _log.error('Falha ao ler pubkey/port: %s', e)
                self._send(500, {'error': str(e)})
        else:
            self._send(404, {'error': 'not found'})

    def do_POST(self):  # noqa: N802
        if not self._authorized():
            self._send(403, {'error': 'forbidden'})
            return

        body = self._read_body()
        if body is None:
            self._send(400, {'error': 'JSON inválido'})
            return

        if self.path == '/peer/add':
            self._add_peer(body)
        elif self.path == '/peer/remove':
            self._remove_peer(body)
        else:
            self._send(404, {'error': 'not found'})

    # ------------------------------------------------------------------
    def _add_peer(self, body: dict):
        public_key = body.get('public_key', '').strip()
        allowed_ips = body.get('allowed_ips', '').strip()
        interface = body.get('interface', _INTERFACE).strip()

        if not public_key or not allowed_ips:
            self._send(400, {'error': 'Campos obrigatórios: public_key, allowed_ips'})
            return

        try:
            _run(['wg', 'set', interface, 'peer', public_key, 'allowed-ips', allowed_ips])
            _run(['wg-quick', 'save', interface])
            _log.info('Peer adicionado: %s... → %s em %s', public_key[:8], allowed_ips, interface)
            self._send(200, {'ok': True})
        except Exception as e:
            _log.error('Falha ao adicionar peer: %s', e)
            self._send(500, {'error': str(e)})

    def _remove_peer(self, body: dict):
        public_key = body.get('public_key', '').strip()
        interface = body.get('interface', _INTERFACE).strip()

        if not public_key:
            self._send(400, {'error': 'Campo obrigatório: public_key'})
            return

        try:
            _run(['wg', 'set', interface, 'peer', public_key, 'remove'])
            _run(['wg-quick', 'save', interface])
            _log.info('Peer removido: %s... de %s', public_key[:8], interface)
            self._send(200, {'ok': True})
        except Exception as e:
            _log.error('Falha ao remover peer: %s', e)
            self._send(500, {'error': str(e)})


def main():
    global _INTERFACE, _SECRET

    parser = argparse.ArgumentParser(description='WireGuard Manager Daemon')
    parser.add_argument('--interface', default='wg0', help='Interface WireGuard (padrão: wg0)')
    parser.add_argument('--port', type=int, default=9999, help='Porta HTTP (padrão: 9999)')
    parser.add_argument('--host', default='127.0.0.1', help='Endereço de bind (padrão: 127.0.0.1)')
    parser.add_argument('--secret', default='', help='Chave secreta X-Secret')
    args = parser.parse_args()

    _INTERFACE = args.interface
    _SECRET = args.secret or None

    server = HTTPServer((args.host, args.port), WgHandler)
    _log.info('Daemon WireGuard iniciado em %s:%d (interface: %s)', args.host, args.port, _INTERFACE)
    if not _SECRET:
        _log.warning('ATENÇÃO: Daemon rodando sem chave secreta. Configure --secret em produção.')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _log.info('Daemon encerrado.')


if __name__ == '__main__':
    main()
