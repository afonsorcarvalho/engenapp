"""Aloca IPs disponíveis do pool WireGuard."""

import ipaddress
from odoo.exceptions import UserError


def allocate_ip(env):
    """Return the next available IP string from the active pool."""
    pool = env['wireguard.ip_pool'].search([('active', '=', True)], limit=1)
    if not pool:
        raise UserError('Nenhum pool de IPs WireGuard configurado.')

    network = ipaddress.ip_network(pool.cidr, strict=False)

    reserved = set()
    if pool.reserved_ips:
        reserved = {ip.strip() for ip in pool.reserved_ips.split(',') if ip.strip()}

    used = set(
        env['wireguard.device'].sudo().search([
            ('assigned_ip', '!=', False),
            ('state', 'in', ['pending', 'active']),
        ]).mapped('assigned_ip')
    )

    unavailable = reserved | used

    for ip in network.hosts():
        ip_str = str(ip)
        if ip_str not in unavailable:
            return ip_str

    raise UserError('Pool de IPs esgotado. Adicione mais IPs ou revogue dispositivos inativos.')
