"""HTTP controller tests for WireGuard enrollment API."""

import json
from unittest.mock import patch, MagicMock

from odoo.tests.common import HttpCase, tagged


_VALID_HW_ID = 'aabb11ccdd22'
_VALID_PUBKEY = 'A' * 43 + '='


def _json_post(client, url, payload):
    return client.url_open(
        url,
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'},
    )


@tagged('post_install', '-at_install', 'wireguard')
class TestEnrollApi(HttpCase):

    def setUp(self):
        super().setUp()
        with self.env.cr.savepoint():
            self.env['wireguard.ip_pool'].create({
                'name': 'Test Pool',
                'cidr': '10.88.0.0/24',
                'reserved_ips': '10.88.0.1',
            })
            self.env['ir.config_parameter'].set_param('web.base.url', 'http://localhost:8069')

    # ------------------------------------------------------------------
    # POST /api/enroll
    # ------------------------------------------------------------------

    def test_enroll_valid(self):
        resp = _json_post(self, '/api/enroll', {
            'device_id': _VALID_HW_ID,
            'public_key': _VALID_PUBKEY,
        })
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertIn('activation_code', body)
        self.assertIn('activation_url', body)
        self.assertIn('poll_url', body)
        self.assertRegex(body['activation_code'], r'^[a-zA-Z0-9]{6,8}$')
        self.assertIn('/activate?code=', body['activation_url'])
        self.assertIn('/api/enroll/status/', body['poll_url'])

    def test_enroll_invalid_device_id(self):
        resp = _json_post(self, '/api/enroll', {
            'device_id': 'TOOSHORT',
            'public_key': _VALID_PUBKEY,
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.json())

    def test_enroll_invalid_pubkey(self):
        resp = _json_post(self, '/api/enroll', {
            'device_id': _VALID_HW_ID,
            'public_key': 'notavalidkey',
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.json())

    def test_enroll_malformed_json(self):
        resp = self.url_open(
            '/api/enroll',
            data=b'not-json',
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(resp.status_code, 400)

    def test_enroll_missing_fields(self):
        resp = _json_post(self, '/api/enroll', {})
        self.assertEqual(resp.status_code, 400)

    def test_enroll_second_request_cancels_first(self):
        resp1 = _json_post(self, '/api/enroll', {
            'device_id': _VALID_HW_ID,
            'public_key': _VALID_PUBKEY,
        })
        resp2 = _json_post(self, '/api/enroll', {
            'device_id': _VALID_HW_ID,
            'public_key': _VALID_PUBKEY,
        })
        self.assertEqual(resp1.status_code, 201)
        self.assertEqual(resp2.status_code, 201)
        code1 = resp1.json()['activation_code']
        code2 = resp2.json()['activation_code']
        self.assertNotEqual(code1, code2)

        # First code is now expired/cancelled
        status_resp = self.url_open(f'/api/enroll/status/{code1}')
        self.assertEqual(status_resp.status_code, 410)

    def test_enroll_rate_limit(self):
        """After 10 attempts from same IP the endpoint returns 429."""
        attempt_model = self.env['wireguard.enroll.attempt'].sudo()
        # Saturate the per-IP limit (10 attempts/hour)
        for i in range(10):
            attempt_model.record_attempt('127.0.0.1', f'aabbccdd{i:04x}')

        resp = _json_post(self, '/api/enroll', {
            'device_id': _VALID_HW_ID,
            'public_key': _VALID_PUBKEY,
        })
        self.assertEqual(resp.status_code, 429)

    # ------------------------------------------------------------------
    # GET /api/enroll/status/<code>
    # ------------------------------------------------------------------

    def test_status_pending(self):
        enroll_resp = _json_post(self, '/api/enroll', {
            'device_id': _VALID_HW_ID,
            'public_key': _VALID_PUBKEY,
        })
        code = enroll_resp.json()['activation_code']
        resp = self.url_open(f'/api/enroll/status/{code}')
        self.assertEqual(resp.status_code, 204)

    def test_status_not_found(self):
        resp = self.url_open('/api/enroll/status/NOTEXIST')
        self.assertEqual(resp.status_code, 404)

    def test_status_expired(self):
        from odoo import fields
        from datetime import timedelta

        enroll_resp = _json_post(self, '/api/enroll', {
            'device_id': _VALID_HW_ID,
            'public_key': _VALID_PUBKEY,
        })
        code = enroll_resp.json()['activation_code']
        enrollment = self.env['wireguard.enrollment'].sudo().search([('code', '=', code)], limit=1)
        enrollment.write({'expires_at': fields.Datetime.now() - timedelta(minutes=1)})

        resp = self.url_open(f'/api/enroll/status/{code}')
        self.assertEqual(resp.status_code, 410)

    @patch('odoo.addons.afr_iot_wireguard.services.wg_runner.requests.post')
    def test_status_activated(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {'ok': True})
        mock_post.return_value.raise_for_status = MagicMock()

        self.env['ir.config_parameter'].sudo().set_param(
            'afr_iot_wireguard.server_public_key', 'B' * 43 + '='
        )
        self.env['ir.config_parameter'].sudo().set_param(
            'afr_iot_wireguard.server_endpoint', 'vpn.test.com:51820'
        )

        enroll_resp = _json_post(self, '/api/enroll', {
            'device_id': _VALID_HW_ID,
            'public_key': _VALID_PUBKEY,
        })
        code = enroll_resp.json()['activation_code']

        # Activate directly via model (bypasses HTTP auth)
        enrollment = self.env['wireguard.enrollment'].sudo().search([('code', '=', code)], limit=1)
        device = enrollment.device_id
        from odoo.addons.afr_iot_wireguard.services.ip_allocator import allocate_ip
        from odoo.addons.afr_iot_wireguard.services.wg_runner import WgRunner
        ip = allocate_ip(self.env)
        WgRunner(self.env).add_peer(_VALID_PUBKEY, ip)
        device.sudo().activate(enrollment, ip)

        resp = self.url_open(f'/api/enroll/status/{code}')
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn('address', body)
        self.assertIn('server_public_key', body)
        self.assertIn('server_endpoint', body)
        self.assertIn('allowed_ips', body)
        self.assertTrue(body['address'].startswith('10.88.0.'))

    # ------------------------------------------------------------------
    # POST /api/device/<hw_id>/revoke
    # ------------------------------------------------------------------

    @patch('odoo.addons.afr_iot_wireguard.services.wg_runner.requests.post')
    def test_revoke_requires_auth(self, _mock):
        """Unauthenticated request is rejected (auth='user' redirects to login)."""
        resp = self.url_open(f'/api/device/{_VALID_HW_ID}/revoke', data=b'')
        # Odoo redirects unauthenticated user requests to /web/login
        self.assertIn(resp.status_code, [302, 303, 401, 403])

    @patch('odoo.addons.afr_iot_wireguard.services.wg_runner.requests.post')
    def test_revoke_active_device(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {'ok': True})
        mock_post.return_value.raise_for_status = MagicMock()

        # Create active device directly
        device = self.env['wireguard.device'].sudo().create({
            'name': 'RevTest',
            'device_hw_id': _VALID_HW_ID,
            'public_key': _VALID_PUBKEY,
            'assigned_ip': '10.88.0.50',
            'state': 'active',
        })

        # Authenticate as admin and add approver group
        self.env.ref('base.user_admin').sudo().groups_id |= self.env.ref(
            'afr_iot_wireguard.group_approver'
        )
        self.authenticate('admin', 'admin')

        resp = self.url_open(
            f'/api/device/{_VALID_HW_ID}/revoke',
            data=b'',
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get('success'))
        device.invalidate_recordset()
        self.assertEqual(device.sudo().state, 'revoked')

    def test_revoke_nonexistent_device(self):
        self.env.ref('base.user_admin').sudo().groups_id |= self.env.ref(
            'afr_iot_wireguard.group_approver'
        )
        self.authenticate('admin', 'admin')
        resp = self.url_open(
            '/api/device/000000000000/revoke',
            data=b'',
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(resp.status_code, 404)
