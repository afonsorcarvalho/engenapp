import logging
import re

from odoo import models, fields, api
from odoo.exceptions import UserError

_log = logging.getLogger(__name__)

_HW_ID_RE = re.compile(r'^[0-9a-fA-F]{12}$')
_PUBKEY_RE = re.compile(r'^[A-Za-z0-9+/]{43}=$')


class WireguardDevice(models.Model):
    _name = 'wireguard.device'
    _description = 'Dispositivo WireGuard'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Nome', required=True, tracking=True)
    device_hw_id = fields.Char(string='ID do Hardware', required=True, index=True, copy=False)
    partner_id = fields.Many2one('res.partner', string='Cliente', tracking=True)
    public_key = fields.Char(string='Chave Pública', readonly=True, copy=False)
    assigned_ip = fields.Char(string='IP Atribuído', readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Rascunho'),
        ('pending', 'Aguardando Ativação'),
        ('active', 'Ativo'),
        ('revoked', 'Revogado'),
    ], string='Estado', default='draft', tracking=True, required=True)
    activated_at = fields.Datetime(string='Ativado em', readonly=True)
    last_handshake_at = fields.Datetime(string='Último Handshake', readonly=True)
    tx_bytes = fields.Integer(string='Bytes Enviados', readonly=True)
    rx_bytes = fields.Integer(string='Bytes Recebidos', readonly=True)
    enrollment_ids = fields.One2many('wireguard.enrollment', 'device_id', string='Enrollments')
    notes = fields.Text(string='Observações')

    _sql_constraints = [
        ('device_hw_id_unique', 'UNIQUE(device_hw_id)', 'O ID do hardware deve ser único.'),
        ('assigned_ip_unique', 'UNIQUE(assigned_ip)', 'IP já atribuído a outro dispositivo.'),
    ]

    @api.constrains('device_hw_id')
    def _check_device_hw_id(self):
        for record in self:
            if not _HW_ID_RE.match(record.device_hw_id):
                raise UserError('ID do hardware deve ser 12 caracteres hexadecimais.')

    @api.constrains('public_key')
    def _check_public_key(self):
        for record in self:
            if record.public_key and not _PUBKEY_RE.match(record.public_key):
                raise UserError('Chave pública deve ser base64-encoded Curve25519 (43 chars + =).')

    @api.constrains('assigned_ip')
    def _check_assigned_ip(self):
        for record in self:
            if record.assigned_ip:
                try:
                    import ipaddress
                    ipaddress.ip_address(record.assigned_ip)
                except ValueError:
                    raise UserError(f'IP inválido: {record.assigned_ip}')

    @api.model
    def find_or_create_by_hw_id(self, hw_id, public_key):
        """Find or create device by hardware ID. Called during enrollment."""
        device = self.search([('device_hw_id', '=', hw_id)], limit=1)
        if device:
            device.write({'public_key': public_key})
            if device.state not in ('active',):
                device.state = 'pending'
        else:
            device = self.create({
                'name': hw_id,
                'device_hw_id': hw_id,
                'public_key': public_key,
                'state': 'pending',
            })
        return device

    def activate(self, enrollment, assigned_ip):
        """Mark device as active after successful WireGuard registration."""
        self.ensure_one()
        self.write({
            'assigned_ip': assigned_ip,
            'state': 'active',
            'activated_at': fields.Datetime.now(),
        })
        enrollment.write({
            'state': 'activated',
            'activated_by': self.env.uid,
            'activated_at': fields.Datetime.now(),
        })
        _log.info('Device activated: hw_id=%s, assigned_ip=%s, user_id=%s',
                  self.device_hw_id, assigned_ip, self.env.uid)
        self.message_post(
            body=f'Dispositivo ativado. IP: {assigned_ip}',
            subtype_id=self.env.ref('mail.mt_note').id,
        )

    def action_revoke(self):
        self.ensure_one()
        if self.state != 'active':
            raise UserError('Apenas dispositivos ativos podem ser revogados.')
        from ..services.wg_runner import WgRunner
        runner = WgRunner(self.env)
        runner.remove_peer(self.public_key)
        self.write({'state': 'revoked'})
        _log.warning('Device revoked: hw_id=%s, assigned_ip=%s, user_id=%s',
                     self.device_hw_id, self.assigned_ip, self.env.uid)
        self.message_post(
            body='Dispositivo revogado manualmente.',
            subtype_id=self.env.ref('mail.mt_note').id,
        )

    def action_new_enrollment(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        enrollment = self.env['wireguard.enrollment'].sudo().create_for_device(self, base_url)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wireguard.enrollment',
            'res_id': enrollment.id,
            'view_mode': 'form',
            'target': 'new',
        }
