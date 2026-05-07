from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    wg_daemon_url = fields.Char(
        string='URL do Daemon WireGuard',
        config_parameter='afr_iot_wireguard.daemon_url',
        default='http://172.17.0.1:9999',
        help='URL do daemon no host (ex: http://172.17.0.1:9999)',
    )
    wg_daemon_secret = fields.Char(
        string='Chave Secreta do Daemon',
        config_parameter='afr_iot_wireguard.daemon_secret',
        help='Chave secreta compartilhada entre Odoo e o daemon',
    )
    wg_interface = fields.Char(
        string='Interface WireGuard',
        config_parameter='afr_iot_wireguard.interface',
        default='wg0',
    )
    wg_server_public_key = fields.Char(
        string='Chave Pública do Servidor',
        config_parameter='afr_iot_wireguard.server_public_key',
        help='Chave pública do WireGuard do servidor (base64)',
    )
    wg_server_endpoint = fields.Char(
        string='Endpoint do Servidor',
        config_parameter='afr_iot_wireguard.server_endpoint',
        help='Ex: vpn.empresa.com:51820',
    )
    wg_client_allowed_ips = fields.Char(
        string='Allowed IPs (cliente)',
        config_parameter='afr_iot_wireguard.client_allowed_ips',
        default='0.0.0.0/0',
        help='Rotas que o dispositivo enviará pelo túnel',
    )
    wg_dns = fields.Char(
        string='DNS',
        config_parameter='afr_iot_wireguard.dns',
        help='Servidor DNS entregue ao dispositivo (ex: 10.8.0.1)',
    )
