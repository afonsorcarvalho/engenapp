# Guia de Instalação em Servidor — afr_iot_wireguard

Passos para configurar do zero um servidor Linux + WireGuard + wg_manager + Odoo (Docker) para o módulo `afr_iot_wireguard`.

Testado em Ubuntu 22.04 LTS. Adapte caminhos/firewall conforme a distro.

---

## 0. Pré-requisitos

- Servidor Linux com IP público estático (VPS, droplet, EC2, etc.).
- Acesso `sudo`.
- Portas abertas no provider:
  - `UDP 51820` — WireGuard (peers IoT)
  - `TCP 8083` (ou outra) — Odoo HTTP, se acessível externamente
- Docker + Docker Compose instalados.

---

## 1. Habilitar IP forwarding no kernel

```bash
echo 'net.ipv4.ip_forward = 1' | sudo tee /etc/sysctl.d/99-wireguard.conf
sudo sysctl --system
```

---

## 2. Instalar WireGuard

```bash
sudo apt update && sudo apt install -y wireguard wireguard-tools
```

---

## 3. Gerar chaves do servidor

```bash
sudo mkdir -p /etc/wireguard && sudo chmod 700 /etc/wireguard
wg genkey | sudo tee /etc/wireguard/server_private.key | wg pubkey | sudo tee /etc/wireguard/server_public.key
sudo chmod 600 /etc/wireguard/server_private.key
```

Anote o conteúdo de `server_public.key` — vai para `ir.config_parameter` no passo 9.

---

## 4. Criar a interface `wg0`

```bash
sudo nano /etc/wireguard/wg0.conf
```

```ini
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = <conteúdo de /etc/wireguard/server_private.key>
SaveConfig = true
PostUp   = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -A FORWARD -o wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -D FORWARD -o wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
```

> Substitua `eth0` pela interface principal do servidor (`ip route show default | awk '{print $5}'`).
> `SaveConfig = true` é importante: o `wg_manager` chama `wg-quick save wg0` após cada `wg set`, persistindo peers no disco.

Ative:

```bash
sudo systemctl enable --now wg-quick@wg0
sudo systemctl status wg-quick@wg0
sudo wg show wg0
```

---

## 5. Firewall do host

```bash
sudo ufw allow 51820/udp comment 'WireGuard'
sudo ufw allow 22/tcp    comment 'SSH'
sudo ufw allow 8083/tcp  comment 'Odoo HTTP'  # se Odoo for público
sudo ufw enable
sudo ufw status verbose
```

No provider (AWS Security Group, GCP firewall, etc.), libere as mesmas portas.

---

## 6. Instalar o `wg_manager` (daemon HTTP control plane)

O daemon corre como root no host (fora do container Docker) e executa `wg set` por trás de uma API HTTP autenticada por `X-Secret`.

Endpoints expostos:
- `GET /health` — público; devolve `{"status":"ok","interface":"wg0"}`
- `GET /pubkey` — requer `X-Secret`; devolve `{"interface","public_key","listen_port"}` (usado pelo Odoo / setup automatizado)
- `POST /peer/add` — requer `X-Secret`; body `{"public_key","allowed_ips"[,"interface"]}`
- `POST /peer/remove` — requer `X-Secret`; body `{"public_key"[,"interface"]}`

Instalar:

```bash
sudo mkdir -p /opt/wg_manager
sudo cp addons/afr_iot_wireguard/wg_daemon/wg_manager.py /opt/wg_manager/
sudo chmod +x /opt/wg_manager/wg_manager.py
sudo cp addons/afr_iot_wireguard/wg_daemon/wg_manager.service /etc/systemd/system/
```

Gerar segredo e configurar o serviço:

```bash
SECRET=$(openssl rand -base64 32)
echo "Guarde este secret: $SECRET"
sudo sed -i "s|TROQUE_ESTA_CHAVE_SECRETA|$SECRET|" /etc/systemd/system/wg_manager.service
```

> Se o daemon precisar aceitar requests de fora do localhost (ex.: Docker bridge), edite a unit para `--host 0.0.0.0`. Em deploy mono-host com Docker, `127.0.0.1` + acesso via `host.docker.internal` basta.

Habilitar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now wg_manager.service
sudo systemctl status wg_manager.service
```

Testar:

```bash
curl http://127.0.0.1:9999/health
# {"status":"ok","interface":"wg0"}

curl -H "X-Secret: $SECRET" http://127.0.0.1:9999/pubkey
# {"interface":"wg0","public_key":"...","listen_port":51820}
```

---

## 7. Subir o stack Odoo (Docker)

```bash
cd /caminho/para/odoo_engenapp
docker compose up -d db
docker compose up -d web
docker compose ps
```

Confirme que `docker-compose.yml` mapeia:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
ports:
  - "8083:8069"
```

---

## 8. Configurar `odoo.conf`

Edite `conf/odoo.conf` (montado em `/etc/odoo` no container) e adicione **antes** de subir o web:

```ini
[options]
addons_path = /mnt/extra-addons, /mnt/engenapp,/mnt/l10n-brazil,/mnt/product-attribute
server_wide_modules = base,web,afr_iot_wireguard
```

A linha `server_wide_modules` é **obrigatória**: carrega o patch `db_router.py` antes de qualquer request, permitindo o roteamento de DB via header `X-Odoo-Db` ou query param `?db=` (necessário em deploys multi-DB sem `dbfilter`). Sem isso, os endpoints `auth='none'` retornam 404/500 quando há mais de uma DB.

Reinicie o container web após editar:

```bash
docker restart $(docker compose ps -q web)
```

---

## 9. Instalar o módulo na DB-alvo

```bash
docker compose exec -u root web /opt/odoo/venv/bin/odoo \
  -d <nome_do_banco> \
  -i afr_iot_wireguard \
  --stop-after-init --no-http \
  --db_host=db --db_port=5432 \
  --db_user=odoo --db_password=odoo
```

Ou via UI: Apps → Update Apps List → procurar "afr_iot_wireguard" → Install.

---

## 10. Configurar parâmetros em `ir.config_parameter`

Opção A — UI: Settings → Technical → Parameters → System Parameters (precisa de developer mode).
Opção B — SQL:

```bash
docker exec -it $(docker compose ps -q db) psql -U odoo -d <nome_do_banco>
```

```sql
INSERT INTO ir_config_parameter (key, value, create_uid, write_uid, create_date, write_date) VALUES
  ('afr_iot_wireguard.daemon_url',        'http://host.docker.internal:9999', 2,2,NOW(),NOW()),
  ('afr_iot_wireguard.daemon_secret',     '<SECRET do passo 6>',              2,2,NOW(),NOW()),
  ('afr_iot_wireguard.interface',         'wg0',                              2,2,NOW(),NOW()),
  ('afr_iot_wireguard.server_public_key', '<conteúdo de server_public.key>',  2,2,NOW(),NOW()),
  ('afr_iot_wireguard.server_endpoint',   '<IP_PUBLICO>:51820',               2,2,NOW(),NOW()),
  ('afr_iot_wireguard.client_allowed_ips','10.0.0.0/24',                      2,2,NOW(),NOW()),
  ('afr_iot_wireguard.dns',               '1.1.1.1',                          2,2,NOW(),NOW())
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, write_date = NOW();

SELECT key, value FROM ir_config_parameter WHERE key LIKE 'afr_iot_wireguard%' ORDER BY key;
```

Após mudar via SQL, **reinicie o container** (cache de `get_param` fica stale):

```bash
docker restart $(docker compose ps -q web)
```

### Referência dos parâmetros

| Chave | Descrição | Exemplo |
|---|---|---|
| `daemon_url`        | URL do `wg_manager` visível pelo container | `http://host.docker.internal:9999` |
| `daemon_secret`     | `X-Secret` do daemon                       | output de `openssl rand -base64 32` |
| `interface`         | Interface WireGuard                        | `wg0` |
| `server_public_key` | Public key do servidor                     | output de `cat /etc/wireguard/server_public.key` |
| `server_endpoint`   | Endpoint público que o ESP32 vai usar      | `203.0.113.4:51820` |
| `client_allowed_ips`| Rotas que o cliente roteia pelo túnel      | `10.0.0.0/24` (LAN apenas) ou `0.0.0.0/0` (full tunnel) |
| `dns`               | DNS opcional servido ao cliente            | `1.1.1.1` |

> Dica: usar `GET /pubkey` no daemon evita copiar manualmente a chave do servidor:
> ```bash
> curl -H "X-Secret: $SECRET" http://127.0.0.1:9999/pubkey
> ```

---

## 11. Criar o pool de IPs

UI: WireGuard → IP Pools → New. Ou SQL:

```sql
INSERT INTO wireguard_ip_pool (name, cidr, reserved_ips, active, create_uid, write_uid, create_date, write_date)
VALUES ('default', '10.0.0.0/24', '10.0.0.1', true, 2,2,NOW(),NOW());
```

CIDR e `reserved_ips` devem bater com a interface `wg0` configurada no passo 4 (servidor é `10.0.0.1`).

---

## 12. Atribuir o grupo aprovador ao admin

```sql
-- ID do grupo
SELECT id FROM ir_model_data WHERE module='afr_iot_wireguard' AND name='group_approver';
-- ID do admin
SELECT id FROM res_users WHERE login='admin';
-- Atribuir
INSERT INTO res_groups_users_rel (gid, uid) VALUES (<gid>, <uid>) ON CONFLICT DO NOTHING;
```

Sem esse grupo, a página `/activate?code=...` retorna "Você não tem permissão para ativar dispositivos WireGuard".

---

## 13. Smoke test end-to-end

Gere uma keypair fictícia e teste o enrollment como se fosse um ESP32:

```bash
PRIV=$(wg genkey); PUB=$(echo "$PRIV" | wg pubkey); DEV=$(openssl rand -hex 6)
echo "device=$DEV pub=$PUB"

curl -X POST http://<HOST>:8083/api/enroll \
  -H 'Content-Type: application/json' \
  -H 'X-Odoo-Db: <nome_do_banco>' \
  -d "{\"device_id\":\"$DEV\",\"public_key\":\"$PUB\"}"
# Esperado: 201 com {"activation_code","activation_url","poll_url"}

# Aprovar abrindo activation_url num browser logado como admin (já contém ?db=...).

# Poll status (substitua <CODE>):
curl -H 'X-Odoo-Db: <nome_do_banco>' http://<HOST>:8083/api/enroll/status/<CODE>
# Pending = 204, Activated = 200 + config completa.
```

Verifique no daemon que o peer foi adicionado:

```bash
sudo wg show wg0 latest-handshakes
```

---

## 14. Re-enrollment (re-keying)

Se um device já está `active` e chama `POST /api/enroll` de novo com uma chave nova:

- O backend **não** exige nova aprovação manual.
- O peer é trocado no daemon (remove pubkey antiga, adiciona a nova) preservando o IP atribuído.
- A enrollment criada já nasce em estado `activated`; o poll seguinte retorna a config WireGuard direta.

> **Risco**: a confiança fica ancorada no `device_hw_id`. Em deploys onde o `hw_id` pode vazar (ex.: dispositivos públicos), considere adicionar um challenge HMAC com factory secret no firmware antes de aceitar re-keying.

---

## 15. Multi-DB — header `X-Odoo-Db` / query `?db=`

O servidor Odoo com várias DBs e sem `dbfilter` precisa que o cliente indique a DB-alvo. O patch `db_router.py` (carregado via `server_wide_modules`) aceita duas formas:

- **ESP32** → manda header `X-Odoo-Db: <dbname>` em cada POST/GET.
- **Browser do admin (QR scan)** → a `activation_url` já inclui `?db=<dbname>&code=...`; basta abrir.

Se quiser hard-lock o servidor numa única DB, use `dbfilter` no `odoo.conf` e o header/param passa a ser opcional:

```ini
dbfilter = ^minha_db$
```

---

## 16. Cron de expiração

O módulo registra um cron `ir.cron` que expira enrollments pendentes após 10 minutos. Verifique:

```sql
SELECT name, active, nextcall FROM ir_cron WHERE model_id IN (SELECT id FROM ir_model WHERE model='wireguard.enrollment');
```

---

## 17. Backup essencial

- `/etc/wireguard/wg0.conf` (peers ativos persistidos)
- `/etc/wireguard/server_private.key`
- Volume Postgres (DB do Odoo)
- `ir.config_parameter` do módulo (já incluído no backup da DB)

---

## Troubleshooting

| Sintoma | Causa provável | Fix |
|---|---|---|
| `POST /api/enroll` → 404 | Module não instalado nessa DB **ou** sem `dbfilter` e sem `X-Odoo-Db` | Instalar módulo / enviar header |
| `POST /api/enroll` → 500 + traceback "DB hint not in available DBs" | Nome de DB errado no header | Verificar lista: `curl -X POST .../web/database/list` |
| Daemon retorna `forbidden` | `daemon_secret` no Odoo ≠ `--secret` no `wg_manager.service` | Realinhar valores e reiniciar daemon + container |
| `ping 10.0.0.X` → `Destination Host Unreachable` | Peer no kernel mas sem handshake (cliente nunca chegou ao server) | Verificar UDP 51820 aberto, NAT/firewall, `wg show wg0 latest-handshakes` |
| Activação no browser → "Você não tem permissão" | User sem grupo `group_approver` | Passo 12 |
| Activação → "Nenhum pool de IPs configurado" | Falta record `wireguard.ip_pool` | Passo 11 |
| `wg show wg0` mostra peers fantasmas após restart | `SaveConfig = false` em `wg0.conf` | Setar `SaveConfig = true` |

---

## Serviços a verificar após setup

```bash
sudo systemctl status wg-quick@wg0
sudo systemctl status wg_manager.service
docker compose ps
sudo wg show wg0
curl http://127.0.0.1:9999/health
```
