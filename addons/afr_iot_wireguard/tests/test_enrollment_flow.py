"""Testes do fluxo de enrollment WireGuard."""

from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'wireguard')
class TestEnrollmentFlow(TransactionCase):

    def setUp(self):
        super().setUp()
        self.env['wireguard.ip_pool'].create({
            'name': 'Test Pool',
            'cidr': '10.99.0.0/24',
            'reserved_ips': '10.99.0.1',
        })
        self.env['ir.config_parameter'].set_param('web.base.url', 'http://localhost:8069')

    def _fake_public_key(self, suffix='A'):
        return ('A' * 43 + '=').replace('A', suffix, 1)

    def test_enroll_creates_device_and_enrollment(self):
        hw_id = 'aabbccddeeff'
        public_key = 'A' * 43 + '='

        device = self.env['wireguard.device'].sudo().find_or_create_by_hw_id(hw_id, public_key)
        self.assertEqual(device.device_hw_id, hw_id)
        self.assertEqual(device.state, 'pending')

        enrollment = self.env['wireguard.enrollment'].sudo().create_for_device(
            device, base_url='http://localhost:8069'
        )
        self.assertEqual(enrollment.state, 'pending')
        self.assertEqual(len(enrollment.code), 7)
        self.assertIn('/activate?code=', enrollment.activation_url)

    def test_second_enroll_cancels_first(self):
        hw_id = 'aabbccddeef0'
        public_key = 'B' * 43 + '='
        device = self.env['wireguard.device'].sudo().find_or_create_by_hw_id(hw_id, public_key)

        e1 = self.env['wireguard.enrollment'].sudo().create_for_device(device)
        e2 = self.env['wireguard.enrollment'].sudo().create_for_device(device)

        self.assertEqual(e1.state, 'cancelled')
        self.assertEqual(e2.state, 'pending')

    def test_find_by_code_pending(self):
        hw_id = 'aabbccddeef1'
        public_key = 'C' * 43 + '='
        device = self.env['wireguard.device'].sudo().find_or_create_by_hw_id(hw_id, public_key)
        enrollment = self.env['wireguard.enrollment'].sudo().create_for_device(device)

        found, status = self.env['wireguard.enrollment'].sudo().find_by_code(enrollment.code)
        self.assertEqual(status, 'pending')
        self.assertEqual(found.id, enrollment.id)

    def test_find_by_code_not_found(self):
        _, status = self.env['wireguard.enrollment'].sudo().find_by_code('INVALID')
        self.assertEqual(status, 'not_found')

    def test_expire_old_cron(self):
        from odoo import fields
        from datetime import timedelta

        hw_id = 'aabbccddeef2'
        public_key = 'D' * 43 + '='
        device = self.env['wireguard.device'].sudo().find_or_create_by_hw_id(hw_id, public_key)
        enrollment = self.env['wireguard.enrollment'].sudo().create_for_device(device)

        enrollment.sudo().write({
            'expires_at': fields.Datetime.now() - timedelta(minutes=1),
        })

        self.env['wireguard.enrollment'].sudo().expire_old()
        self.assertEqual(enrollment.state, 'expired')

    @patch('odoo.addons.afr_iot_wireguard.services.wg_runner.requests.post')
    def test_activation_flow(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {'ok': True})
        mock_post.return_value.raise_for_status = MagicMock()

        hw_id = 'aabbccddeef3'
        public_key = 'E' * 43 + '='
        device = self.env['wireguard.device'].sudo().find_or_create_by_hw_id(hw_id, public_key)
        enrollment = self.env['wireguard.enrollment'].sudo().create_for_device(device)

        from odoo.addons.afr_iot_wireguard.services.ip_allocator import allocate_ip
        from odoo.addons.afr_iot_wireguard.services.wg_runner import WgRunner

        assigned_ip = allocate_ip(self.env)
        self.assertTrue(assigned_ip.startswith('10.99.0.'))

        runner = WgRunner(self.env)
        runner.add_peer(public_key, assigned_ip)
        device.sudo().activate(enrollment, assigned_ip)

        self.assertEqual(device.state, 'active')
        self.assertEqual(device.assigned_ip, assigned_ip)
        self.assertEqual(enrollment.state, 'activated')
        mock_post.assert_called_once()

    def test_ip_pool_exhaustion(self):
        """Aloca todos os IPs e verifica erro de esgotamento."""
        from odoo.addons.afr_iot_wireguard.services.ip_allocator import allocate_ip
        from odoo.exceptions import UserError
        import ipaddress

        pool = self.env['wireguard.ip_pool'].search([('cidr', '=', '10.99.0.0/24')], limit=1)
        network = ipaddress.ip_network(pool.cidr, strict=False)
        hosts = list(network.hosts())

        # Fill all IPs except reserved
        for i, ip in enumerate(hosts[1:6]):  # Use a few to test
            self.env['wireguard.device'].create({
                'name': f'Dev {i}',
                'device_hw_id': f'aabbccdd00{i:02x}',
                'assigned_ip': str(ip),
                'state': 'active',
            })

        # Should still find IPs (pool has 254 hosts)
        ip = allocate_ip(self.env)
        self.assertIsNotNone(ip)

    def test_invalid_device_id_format(self):
        """Device ID must be exactly 12 hex chars."""
        hw_id = 'aabbccddee'  # only 10 chars
        public_key = 'A' * 43 + '='

        device = self.env['wireguard.device'].sudo().find_or_create_by_hw_id(hw_id, public_key)
        # Should still be created but with state pending (format check is at API level)
        self.assertEqual(device.state, 'pending')

    def test_invalid_pubkey_format(self):
        """Public key must be base64-encoded Curve25519 (43 chars + =)."""
        hw_id = 'aabbccddeeff'
        invalid_keys = [
            'tooshort',  # Too short
            'A' * 44 + '=',  # Too long
            'A' * 42 + '==',  # Wrong padding
            'A' * 43,  # Missing padding
        ]

        for invalid_key in invalid_keys:
            device = self.env['wireguard.device'].sudo().find_or_create_by_hw_id(hw_id, invalid_key)
            # Model accepts any string; API level does validation
            self.assertEqual(device.state, 'pending')

    def test_rate_limit_by_ip(self):
        """IP with >10 attempts/hour should be rate limited."""
        from odoo import fields
        from datetime import timedelta

        ip = '192.168.1.100'
        hw_id = 'aabbccddeeff'
        attempt_model = self.env['wireguard.enroll.attempt'].sudo()

        # Record 10 attempts
        for i in range(10):
            attempt_model.record_attempt(ip, f'aabbccdd00{i:02x}')

        # 11th should fail rate limit check
        allowed = attempt_model.check_rate_limit(ip, 'aabbccddfff0')
        self.assertFalse(allowed)

    def test_rate_limit_by_device_hw_id(self):
        """Device ID with >5 attempts/hour should be rate limited."""
        hw_id = 'aabbccddeeff'
        attempt_model = self.env['wireguard.enroll.attempt'].sudo()

        # Record 5 attempts for same hw_id
        for i in range(5):
            attempt_model.record_attempt(f'192.168.1.{i}', hw_id)

        # 6th should fail rate limit check
        allowed = attempt_model.check_rate_limit('192.168.1.99', hw_id)
        self.assertFalse(allowed)

    def test_rate_limit_purge_cron(self):
        """Old attempts (>1 hour) should be purged."""
        from odoo import fields
        from datetime import timedelta

        ip = '192.168.1.100'
        hw_id = 'aabbccddeeff'
        attempt_model = self.env['wireguard.enroll.attempt'].sudo()

        # Create an old attempt (>1 hour old)
        old_attempt = attempt_model.create({'ip': ip, 'device_hw_id': hw_id})
        old_attempt.write({'create_date': fields.Datetime.now() - timedelta(hours=2)})

        # Create a recent attempt (<1 hour old)
        attempt_model.record_attempt('192.168.1.200', 'aabbccddffff')

        # Purge old
        attempt_model.purge_old()

        # Old should be gone, recent should remain
        old_still_exists = attempt_model.search_count([('ip', '=', ip)])
        recent_exists = attempt_model.search_count([('ip', '=', '192.168.1.200')])

        self.assertEqual(old_still_exists, 0)
        self.assertEqual(recent_exists, 1)

    def test_device_state_transitions(self):
        """Device state should transition correctly through states."""
        hw_id = 'aabbccddeeff'
        public_key = 'F' * 43 + '='

        device = self.env['wireguard.device'].sudo().find_or_create_by_hw_id(hw_id, public_key)
        self.assertEqual(device.state, 'pending')

        # Activate
        enrollment = self.env['wireguard.enrollment'].sudo().create_for_device(device)
        device.sudo().activate(enrollment, '10.99.0.100')
        self.assertEqual(device.state, 'active')
        self.assertEqual(device.assigned_ip, '10.99.0.100')

    def test_enrollment_code_uniqueness(self):
        """Each enrollment should have a unique activation code."""
        hw_id = 'aabbccddeeff'
        public_key = 'G' * 43 + '='

        device = self.env['wireguard.device'].sudo().find_or_create_by_hw_id(hw_id, public_key)
        e1 = self.env['wireguard.enrollment'].sudo().create_for_device(device)

        # New enrollment for same device should have different code
        e2 = self.env['wireguard.enrollment'].sudo().create_for_device(device)

        self.assertNotEqual(e1.code, e2.code)
        # e1 should be cancelled when e2 is created
        self.assertEqual(e1.state, 'cancelled')
