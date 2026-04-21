import logging
import re
import secrets
import string
from datetime import timedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError

_log = logging.getLogger(__name__)

_CODE_CHARS = string.ascii_letters + string.digits
_CODE_TTL_MINUTES = 10
_CODE_RE = re.compile(r'^[a-zA-Z0-9]{6,8}$')


def _generate_code(length=7):
    return ''.join(secrets.choice(_CODE_CHARS) for _ in range(length))


class WireguardEnrollment(models.Model):
    _name = 'wireguard.enrollment'
    _description = 'Solicitação de Enrollment WireGuard'
    _order = 'create_date desc'
    _rec_name = 'code'

    device_id = fields.Many2one(
        'wireguard.device', string='Dispositivo', required=True, ondelete='cascade', index=True,
    )
    code = fields.Char(string='Código de Ativação', required=True, readonly=True, copy=False, index=True)
    activation_url = fields.Char(string='URL de Ativação', readonly=True)
    state = fields.Selection([
        ('pending', 'Pendente'),
        ('activated', 'Ativado'),
        ('expired', 'Expirado'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='pending', required=True)
    expires_at = fields.Datetime(string='Expira em', required=True)
    created_by_ip = fields.Char(string='IP de Origem')
    activated_by = fields.Many2one('res.users', string='Ativado por', readonly=True)
    activated_at = fields.Datetime(string='Ativado em', readonly=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Código de ativação deve ser único.'),
    ]

    @api.constrains('code')
    def _check_code_format(self):
        for record in self:
            if not _CODE_RE.match(record.code):
                raise ValidationError('Código deve ter 6-8 caracteres alfanuméricos.')

    @api.model
    def create_for_device(self, device, base_url=None, request_ip=None):
        """Cancel existing pending enrollments and create a new one."""
        pending = self.search([('device_id', '=', device.id), ('state', '=', 'pending')])
        if pending:
            pending.write({'state': 'cancelled'})
            _log.info('Cancelled %d pending enrollments for device hw_id=%s',
                      len(pending), device.device_hw_id)

        code = _generate_code()
        expires_at = fields.Datetime.now() + timedelta(minutes=_CODE_TTL_MINUTES)

        if not base_url:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')

        activation_url = f'{base_url}/activate?code={code}' if base_url else ''

        enrollment = self.create({
            'device_id': device.id,
            'code': code,
            'activation_url': activation_url,
            'expires_at': expires_at,
            'created_by_ip': request_ip,
        })
        _log.info('Enrollment created: device_hw_id=%s, request_ip=%s',
                  device.device_hw_id, request_ip)
        return enrollment

    @api.model
    def find_by_code(self, code):
        """Return (enrollment, status) where status is one of:
        'pending', 'activated', 'expired', 'cancelled', 'not_found'.
        """
        enrollment = self.search([('code', '=', code)], limit=1)
        if not enrollment:
            return None, 'not_found'
        if enrollment.state in ('activated', 'expired', 'cancelled'):
            return enrollment, enrollment.state
        if fields.Datetime.now() > enrollment.expires_at:
            enrollment.write({'state': 'expired'})
            return enrollment, 'expired'
        return enrollment, 'pending'

    @api.model
    def expire_old(self):
        """Expire pending enrollments past their TTL. Called by cron."""
        expired = self.search([
            ('state', '=', 'pending'),
            ('expires_at', '<', fields.Datetime.now()),
        ])
        if expired:
            expired.write({'state': 'expired'})
