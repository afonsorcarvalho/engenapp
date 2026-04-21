import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import ipaddress

_log = logging.getLogger(__name__)


class WireguardIpPool(models.Model):
    _name = 'wireguard.ip_pool'
    _description = 'Pool de IPs WireGuard'
    _rec_name = 'name'

    name = fields.Char(string='Nome', required=True)
    cidr = fields.Char(string='CIDR', required=True, help='Ex: 10.8.0.0/24')
    reserved_ips = fields.Char(
        string='IPs Reservados',
        help='IPs separados por vírgula que não serão atribuídos (ex: 10.8.0.1,10.8.0.2)',
    )
    active = fields.Boolean(default=True)
    device_count = fields.Integer(string='Dispositivos Ativos', compute='_compute_device_count')

    @api.depends('active')
    def _compute_device_count(self):
        for pool in self:
            pool.device_count = self.env['wireguard.device'].search_count([
                ('assigned_ip', '!=', False),
                ('state', 'in', ['pending', 'active']),
            ])

    @api.constrains('cidr')
    def _check_cidr(self):
        for pool in self:
            try:
                ipaddress.ip_network(pool.cidr, strict=False)
            except ValueError:
                raise ValidationError(f'CIDR inválido: {pool.cidr}')

    @api.constrains('reserved_ips', 'cidr')
    def _check_reserved_ips(self):
        for pool in self:
            if not pool.reserved_ips:
                continue
            try:
                network = ipaddress.ip_network(pool.cidr, strict=False)
            except ValueError:
                return  # _check_cidr already catches CIDR errors
            reserved_list = [ip.strip() for ip in pool.reserved_ips.split(',') if ip.strip()]
            for ip_str in reserved_list:
                try:
                    ip = ipaddress.ip_address(ip_str)
                except ValueError:
                    raise ValidationError(f'IP reservado inválido: {ip_str!r}')
                if ip not in network:
                    raise ValidationError(f'IP reservado {ip_str} não está na rede {pool.cidr}')
