from datetime import timedelta

from odoo import models, fields, api


class WireguardEnrollAttempt(models.Model):
    _name = 'wireguard.enroll.attempt'
    _description = 'Tentativa de Enrollment WireGuard'

    ip = fields.Char(string='IP', required=True, index=True)
    device_hw_id = fields.Char(string='ID do Hardware', required=True, index=True)

    @api.model
    def check_rate_limit(self, ip, device_hw_id):
        """Check if IP or device_hw_id has exceeded rate limit in last hour.
        Returns True if allowed, False if rate limited.
        """
        since = fields.Datetime.now() - timedelta(hours=1)

        ip_count = self.search_count([('ip', '=', ip), ('create_date', '>=', since)])
        if ip_count >= 10:
            return False

        hw_count = self.search_count([('device_hw_id', '=', device_hw_id), ('create_date', '>=', since)])
        if hw_count >= 5:
            return False

        return True

    @api.model
    def record_attempt(self, ip, device_hw_id):
        """Record a new enrollment attempt."""
        self.create({'ip': ip, 'device_hw_id': device_hw_id})

    @api.model
    def purge_old(self):
        """Cron: Remove attempts older than 1 hour."""
        cutoff = fields.Datetime.now() - timedelta(hours=1)
        old = self.search([('create_date', '<', cutoff)])
        if old:
            old.unlink()
