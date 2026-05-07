# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Module overview

`afr_iot_wireguard` is an Odoo 16 (Community) custom module for managing IoT devices that self-provision as WireGuard VPN peers via QR code enrollment. IoT devices (ESP32-S3) generate Curve25519 key pairs locally, call a REST API to request enrollment, and receive WireGuard configuration after an admin scans the QR code and confirms activation. The server never handles private keys.

## Development commands

Install the module:
```bash
odoo-bin -i afr_iot_wireguard -d <database>
```

Update the module:
```bash
odoo-bin -u afr_iot_wireguard -d <database>
```

Run tests (single module):
```bash
odoo-bin --test-enable --stop-after-init -i afr_iot_wireguard -d <test_db>
```

Run a specific test class:
```bash
odoo-bin --test-enable --stop-after-init --test-tags afr_iot_wireguard.TestEnrollmentFlow -d <test_db>
```

## Architecture

### Enrollment flow

1. Device POSTs `{device_id, public_key}` to `POST /api/enroll` → receives `activation_code`, `activation_url`, `poll_url`.
2. Device displays QR with `activation_url`.
3. Admin scans QR, authenticates in Odoo, confirms at `GET/POST /activate?code=<code>`.
4. Odoo allocates IP, calls `wg set` on the host interface, marks enrollment `activated`.
5. Device long-polls `GET /api/enroll/status/<code>` → receives full WireGuard config (address, server public key, endpoint, allowed IPs).

### Key models (`models/`)

- `wireguard.device` — the physical device. Holds `public_key`, `assigned_ip`, `state` (draft/pending/active/revoked). Inherits `mail.thread`.
- `wireguard.enrollment` — single enrollment request. Has `code` (unique, url-safe, TTL 10 min), `state` (pending/activated/expired/cancelled), `expires_at`.
- `wireguard.ip_pool` — CIDR pool config; one record per WireGuard interface.
- `res.config.settings` extension — stores server public key, server endpoint, and interface name.

### Services (`services/`)

- `wg_runner.py` — wraps all `subprocess.run(['wg', 'set', ...])` calls. Always uses list args (never `shell=True`). After `wg set`, runs `wg-quick save <iface>`. Timeout 5s. Logs stderr to device chatter.
- `ip_allocator.py` — allocates IPs from `wireguard.ip_pool`, avoiding reserved IPs.

### Controllers (`controllers/`)

- `api.py` — `POST /api/enroll` (`auth='none'`, `csrf=False`) and `GET /api/enroll/status/<code>` (`auth='none'`). Controllers only validate and delegate; business logic lives in models/services.
- `activate.py` — `GET/POST /activate` (`auth='user'`, `csrf=True`). Mobile-first QWeb template.

### Security

- `security/ir.model.access.csv` — ACLs per model.
- `security/wireguard_security.xml` — group `wireguard_enrollment.group_approver`; record rules for multi-tenant (device visible only to its `partner_id`).
- `data/ir_cron.xml` — cron to expire stale pending enrollments; optional cron for `wg show` stats collection.

## Key constraints

- `public_key` input must be validated as base64-encoded 32 bytes before use.
- `device_id` is a 12-char hex string; validate format on enrollment.
- Never log public keys at INFO level or above.
- Rate-limit `POST /api/enroll` (table of attempts + cron sweep, no middleware dependency).
- Activation codes are 6–8 url-safe chars, single-use, expire in 10 minutes. A new enrollment for the same `device_id` invalidates the previous pending one.
- All `wg` calls via subprocess list args — never interpolate user input into a shell string.
- Long-running WireGuard calls must not block HTTP request threads; use `ir.cron` or job queue for any operation >5s.

## Conventions

- UI strings in **Portuguese**; docstrings and code comments in **English**.
- Odoo XML IDs prefixed `afr_iot_wireguard.`.
- Module technical name in Python/XML: `afr_iot_wireguard`.
