# afr_iot_wireguard

Odoo 16 module for managing IoT devices that self-provision as WireGuard VPN peers via QR code enrollment.

## Overview

**afr_iot_wireguard** enables IoT devices (ESP32-S3, etc.) to:
1. Generate Curve25519 key pairs locally (never shared with the server)
2. Request enrollment via REST API with their public key
3. Receive an activation URL with a unique QR code
4. Have an admin scan the QR and approve activation
5. Receive full WireGuard configuration (IP, server key, endpoint, allowed IPs)

The server never handles device private keys, ensuring end-to-end security.

## Installation

### 1. Install the Odoo Module

```bash
odoo -i afr_iot_wireguard -d <database>
```

Update an existing installation:
```bash
odoo -u afr_iot_wireguard -d <database>
```

### 2. Deploy WireGuard Daemon (Host System)

The module requires a daemon running on the **host system** (outside Docker) to manage WireGuard interface commands. This daemon is called from Odoo to add/remove peers.

#### 2.1 Copy daemon to host

```bash
sudo cp wg_daemon/wg_manager.py /opt/wg_manager/
sudo chmod +x /opt/wg_manager/wg_manager.py
```

#### 2.2 Install systemd service

```bash
sudo cp wg_daemon/wg_manager.service /etc/systemd/system/
sudo systemctl daemon-reload
```

#### 2.3 Configure and start

Edit `/etc/systemd/system/wg_manager.service` to set:
- `--interface` (WireGuard interface name, default: `wg0`)
- `--port` (HTTP server port, default: `9999`)
- `--secret` (API authentication token, **change this**)

```bash
sudo systemctl enable wg_manager
sudo systemctl start wg_manager
sudo systemctl status wg_manager
```

Check logs:
```bash
sudo journalctl -u wg_manager -f
```

## Docker Installation

This project runs Odoo 16 in Docker. The `docker-compose.yml` in the repo root defines the setup.

### Module files (already mounted)

The `addons/` directory is mounted into the container at `/mnt/extra-addons`, so no copy step is needed — the module is available as soon as the container starts.

### Install via Odoo UI (recommended for dev)

With `--dev=all` the web service reloads automatically:

1. Open `http://localhost:8083/web`
2. Go to **Apps** → click **Update Apps List**
3. Search for **IoT WireGuard Enrollment**
4. Click **Install**

### Install via CLI

Stop the running container first to avoid DB conflicts:

```bash
docker compose stop web

docker compose run --rm web \
  -i afr_iot_wireguard \
  -d <database> \
  --stop-after-init

docker compose start web
```

> **Note:** The entrypoint intercepts arguments starting with `-` and forwards them to `odoo`. Do not prefix with `odoo-bin`.

### Update via CLI

```bash
docker compose stop web

docker compose run --rm web \
  -u afr_iot_wireguard \
  -d <database> \
  --stop-after-init

docker compose start web
```

### Run tests in Docker

```bash
docker compose stop web

docker compose run --rm web \
  --test-enable \
  --stop-after-init \
  -i afr_iot_wireguard \
  -d test_wg

docker compose start web
```

Run only HTTP controller tests:

```bash
docker compose stop web

docker compose run --rm web \
  --test-enable \
  --stop-after-init \
  --test-tags afr_iot_wireguard.TestEnrollApi \
  -i afr_iot_wireguard \
  -d test_wg

docker compose start web
```

### Daemon URL from inside Docker

Odoo runs inside Docker; the `wg_manager` daemon runs on the **host**. The `docker-compose.yml` maps `host.docker.internal → host-gateway`, so use:

```
http://host.docker.internal:9999
```

The default `172.17.0.1` also works if the Docker bridge IP hasn't changed, but `host.docker.internal` is more portable.

Set this in **Settings → WireGuard → Daemon URL** after installing.

### Verify daemon reachability from inside container

```bash
docker compose exec web curl -s http://host.docker.internal:9999/health
# Expected: {"status": "ok", "interface": "wg0"}
```

---

## Configuration

### Odoo Settings

Go to **Settings > Technical > WireGuard Configuration** to set:

| Setting | Default | Description |
|---------|---------|-------------|
| **Server Public Key** | — | WireGuard server's public key (Curve25519 base64) |
| **Server Endpoint** | — | Public IP:port where clients reach the VPN (e.g., `203.0.113.1:51820`) |
| **Interface Name** | `wg0` | WireGuard interface on the host |
| **Daemon URL** | `http://172.17.0.1:9999` | HTTP endpoint of wg_manager daemon |
| **Daemon Secret** | — | Must match `--secret` in wg_manager service |
| **IP Pool CIDR** | `10.0.0.0/24` | Subnet for client allocations |
| **Reserved IPs** | `10.0.0.1` | IPs never assigned to clients (comma-separated) |
| **Client Allowed IPs** | `0.0.0.0/0` | Routes advertised to clients |
| **DNS** | — | DNS servers for clients (optional, comma-separated) |

### IP Pool

Create at least one **IP Pool** record:
- **Name**: Descriptive name (e.g., "Main Pool")
- **CIDR**: Network range (e.g., `10.0.0.0/24`)
- **Active**: Checked
- **Reserved IPs**: Comma-separated (e.g., `10.0.0.1,10.0.0.254`)

## Usage

### Enrollment Flow

1. **Device initiates enrollment** via REST:
   ```bash
   curl -X POST http://odoo-server/api/enroll \
     -H "Content-Type: application/json" \
     -d '{
       "device_id": "aabbccddeeff",
       "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
     }'
   ```
   Response:
   ```json
   {
     "activation_code": "aBc123",
     "activation_url": "http://odoo-server/activate?code=aBc123",
     "poll_url": "http://odoo-server/api/enroll/status/aBc123"
   }
   ```

2. **Device displays QR code** with `activation_url`

3. **Admin scans QR** in Odoo interface:
   - Authenticates to Odoo
   - Reviews device details
   - Clicks **Confirm Activation**
   - Odoo allocates IP from pool
   - Daemon adds peer to WireGuard interface
   - Device marked as **Active**

4. **Device polls for config** via `GET /api/enroll/status/<code>`:
   ```json
   {
     "address": "10.0.0.100/24",
     "server_public_key": "...",
     "server_endpoint": "203.0.113.1:51820",
     "allowed_ips": "0.0.0.0/0",
     "dns": "8.8.8.8"
   }
   ```

5. **Device configures WireGuard** and connects

### Admin Operations

#### View Devices
Go to **IoT > WireGuard Devices**. Filter by state:
- **Draft**: Unconfigured
- **Pending**: Waiting for admin approval
- **Active**: Connected to VPN
- **Revoked**: Manually disabled

#### Approve Enrollment
1. Go to **IoT > Enrollments**
2. Click pending enrollment
3. Click **Confirm Activation**
4. Optionally assign the device to a customer

#### Revoke Access
1. Open device in **Active** state
2. Click **Revoke** button
3. Device removed from WireGuard immediately

#### View Stats
Device details show:
- Last handshake timestamp
- Bytes sent/received
- Enrollment history
- Chatter for audit trail

## Testing

### Run all module tests
```bash
odoo-bin --test-enable --stop-after-init -i afr_iot_wireguard -d test_db
```

### Run specific test class
```bash
odoo-bin --test-enable --stop-after-init \
  --test-tags afr_iot_wireguard.TestEnrollmentFlow \
  -d test_db
```

### Manual API testing

Start Odoo and test enrollment:
```bash
python3 -c "
import requests
import json

data = {
    'device_id': 'aabbccddeeff',
    'public_key': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
}
resp = requests.post('http://localhost:8069/api/enroll', json=data)
print(json.dumps(resp.json(), indent=2))
"
```

## Security Notes

- **Device Private Keys**: Never sent to server. Devices keep full control.
- **Public Keys**: Validated as base64-encoded 32-byte Curve25519 keys.
- **Device IDs**: Must be 12-char hex strings; rate-limited to prevent enumeration.
- **Activation Codes**: 7-char alphanumeric, single-use, expire in 10 minutes.
- **Daemon Communication**: Uses HTTP with optional shared secret (set `--secret` in systemd service).
- **Multi-tenant**: Devices visible only to assigned customers (via `partner_id` record rules).

## Architecture

### Models
- **wireguard.device** — Physical device, state machine (draft → pending → active → revoked)
- **wireguard.enrollment** — Enrollment request, activation code, TTL management
- **wireguard.ip_pool** — CIDR configuration for IP allocation
- **res.config.settings** — Server config (keys, endpoints, daemon connection)

### Services
- **ip_allocator.py** — Allocates unused IPs from pool, respects reserved ranges
- **wg_runner.py** — HTTP client to wg_manager daemon; handles errors and timeouts

### Daemon (Host)
- **wg_manager.py** — Standalone Python HTTP server; runs as root on host; executes `wg` commands

### Controllers
- **api.py** — Public REST endpoints (`/api/enroll`, `/api/enroll/status/<code>`)
- **activate.py** — Admin approval interface (`/activate?code=<code>`)

### Cron Jobs
- Expires stale pending enrollments (10+ minutes old)
- Optional: Collects WireGuard stats (handshakes, bytes)

## Troubleshooting

### Daemon connection fails
- Check daemon is running: `sudo systemctl status wg_manager`
- Verify network connectivity from Docker: `docker exec <odoo-container> curl http://172.17.0.1:9999/health`
- Check logs: `sudo journalctl -u wg_manager -f`
- Verify `--secret` matches Odoo configuration

### IP allocation fails
- Ensure IP pool is created and marked **Active**
- Check CIDR syntax (e.g., `10.0.0.0/24`)
- Verify reserved IPs don't overlap with pool range

### Device doesn't receive config
- Check enrollment state: should be **Activated**
- Verify poll endpoint: `GET /api/enroll/status/<code>` returns 200, not 204
- Check device has assigned IP in database

### Device can't reach VPN endpoint
- Verify `server_endpoint` in settings (must be public IP:port)
- Check WireGuard interface is active: `sudo wg show wg0`
- Check firewall allows UDP 51820 (or configured port)

## Development

### Install module (dev)
```bash
odoo-bin -i afr_iot_wireguard -d <database> --dev=all
```

### Watch for changes
```bash
odoo-bin -u afr_iot_wireguard -d <database>
```

### Debug daemon
```bash
sudo python3 /opt/wg_manager/wg_manager.py \
  --interface wg0 \
  --host 127.0.0.1 \
  --port 9999 \
  --secret test_secret
```

### Database inspection
```sql
-- Recent enrollments
SELECT code, state, expires_at FROM wireguard_enrollment ORDER BY create_date DESC LIMIT 10;

-- Active devices
SELECT name, assigned_ip, state FROM wireguard_device WHERE state = 'active';

-- IP allocations
SELECT device_hw_id, assigned_ip FROM wireguard_device WHERE assigned_ip IS NOT NULL;
```

## License

LGPL-3.0
