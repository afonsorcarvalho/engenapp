# Guia de Configuração do Servidor — afr_iot_wireguard

Passos para configurar um novo servidor com WireGuard + wg_manager + Odoo.

---

## 1. Instalar o WireGuard

```bash
sudo apt update && sudo apt install -y wireguard
```

---

## 2. Gerar chaves do servidor

```bash
wg genkey | sudo tee /etc/wireguard/server_private.key | wg pubkey | sudo tee /etc/wireguard/server_public.key
sudo chmod 600 /etc/wireguard/server_private.key
```

---

## 3. Criar a interface wg0

```bash
sudo nano /etc/wireguard/wg0.conf
```

Conteúdo:

```ini
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = <conteúdo de server_private.key>
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -A FORWARD -o wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -D FORWARD -o wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
```

> Substitua `eth0` pela interface de rede principal do servidor (`ip route | grep default`).

---

## 4. Ativar e perpetuar o WireGuard

```bash
sudo systemctl enable wg-quick@wg0
sudo systemctl start wg-quick@wg0
sudo systemctl status wg-quick@wg0
```

---

## 5. Instalar o wg_manager

Copie o ficheiro `wg_daemon/wg_manager.py` para o servidor e instale como serviço systemd:

```bash
sudo mkdir -p /opt/wg_manager
sudo cp wg_daemon/wg_manager.py /opt/wg_manager/
sudo chmod +x /opt/wg_manager/wg_manager.py
sudo cp wg_daemon/wg_manager.service /etc/systemd/system/
```

---

## 6. Gerar e configurar a chave secreta do wg_manager

```bash
SECRET=$(openssl rand -base64 32)
echo "Guarde esta chave: $SECRET"

sudo sed -i "s/TROQUE_ESTA_CHAVE_SECRETA/$SECRET/" /etc/systemd/system/wg_manager.service
```

Ative e inicie o serviço:

```bash
sudo systemctl daemon-reload
sudo systemctl enable wg_manager.service
sudo systemctl start wg_manager.service
sudo systemctl status wg_manager.service
```

Teste o health check:

```bash
curl localhost:9999/health
# Esperado: {"status": "ok", "interface": "wg0"}
```

---

## 7. Instalar o módulo no Odoo (via Docker)

```bash
cd /home/afonso/docker/odoo_engenapp

docker compose exec -u root web /opt/odoo/venv/bin/odoo \
  -d <nome_do_banco> \
  -i afr_iot_wireguard \
  --stop-after-init --no-http \
  --db_host=db --db_port=5432 \
  --db_user=odoo --db_password=odoo
```

---

## 8. Atualizar os parâmetros no banco de dados

Conecte ao banco:

```bash
docker exec -it odoo_engenapp-db-1 psql -U odoo -d <nome_do_banco>
```

Execute:

```sql
-- URL do wg_manager (acessível de dentro do container)
UPDATE ir_config_parameter SET value = 'http://host.docker.internal:9999'
WHERE key = 'afr_iot_wireguard.daemon_url';

-- Chave secreta (a mesma gerada no passo 6)
UPDATE ir_config_parameter SET value = '<SECRET>'
WHERE key = 'afr_iot_wireguard.daemon_secret';

-- Public key do servidor WireGuard
UPDATE ir_config_parameter SET value = '<conteúdo de /etc/wireguard/server_public.key>'
WHERE key = 'afr_iot_wireguard.server_public_key';

-- Endpoint público do servidor (IP:porta)
UPDATE ir_config_parameter SET value = '<IP_PUBLICO>:51820'
WHERE key = 'afr_iot_wireguard.server_endpoint';
```

Confirme os valores:

```sql
SELECT key, value FROM ir_config_parameter WHERE key LIKE 'afr_iot_wireguard%' ORDER BY key;
```

---

## 9. Adicionar o admin ao grupo aprovador

```bash
# Via RPC (substitua a sessão por uma válida após login)
curl -X POST http://localhost:<porta_odoo>/web/dataset/call_kw \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=<session>" \
  -d '{
    "jsonrpc": "2.0", "method": "call",
    "params": {
      "model": "res.users",
      "method": "write",
      "args": [[<uid_admin>], {"groups_id": [[4, <id_grupo_approver>]]}],
      "kwargs": {}
    }
  }'
```

Ou via SQL:

```sql
-- Obter o ID do grupo
SELECT id FROM res_groups WHERE name->>'en_US' = 'Aprovador de Dispositivos';

-- Obter o UID do admin
SELECT id FROM res_users WHERE login = 'admin';

-- Adicionar ao grupo
INSERT INTO res_groups_users_rel (gid, uid) VALUES (<gid>, <uid>)
ON CONFLICT DO NOTHING;
```

---

## 10. Verificação final

```bash
# Health check do wg_manager a partir do container Odoo
docker exec odoo_engenapp-web-1 curl -s \
  -H "X-Secret: <SECRET>" \
  http://host.docker.internal:9999/health

# Testar enrollment completo
curl -X POST http://localhost:<porta_odoo>/api/enroll \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=<session>" \
  -d '{"device_id": "aabbccdd1122", "public_key": "<pubkey_base64>"}'
```

---

## Referência rápida — parâmetros do Odoo

| Chave (`ir.config_parameter`) | Descrição |
|-------------------------------|-----------|
| `afr_iot_wireguard.daemon_url` | URL do wg_manager (`http://host.docker.internal:9999`) |
| `afr_iot_wireguard.daemon_secret` | Chave secreta `X-Secret` |
| `afr_iot_wireguard.interface` | Interface WireGuard (`wg0`) |
| `afr_iot_wireguard.server_public_key` | Public key do servidor WireGuard |
| `afr_iot_wireguard.server_endpoint` | Endpoint público (`IP:51820`) |
| `afr_iot_wireguard.client_allowed_ips` | Rotas enviadas ao cliente (padrão: `0.0.0.0/0`) |
| `afr_iot_wireguard.dns` | DNS enviado ao cliente (opcional) |

---

## Serviços a verificar após setup

```bash
sudo systemctl status wg-quick@wg0
sudo systemctl status wg_manager.service
docker compose ps
```
