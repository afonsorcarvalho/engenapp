# F0 — Setup Ollama + pgvector

Sobe stack LLM local e ativa pgvector. Não toca código Odoo — usa provider `lmstudio` (OpenAI-compat) já existente.

## 1. Subir containers

```bash
cd /home/afonso/docker/odoo_engenapp
docker compose -f docker-compose.yml -f docker-compose.ollama.yml up -d
```

Verifica:

```bash
docker compose ps
docker compose logs --tail=50 ollama
```

## 2. Baixar modelo

```bash
chmod +x scripts/ollama_pull.sh
bash scripts/ollama_pull.sh
```

Deve imprimir resposta do modelo no final (smoke test).

## 3. Ativar pgvector no DB do Odoo

Substituir `<DB>` pelo nome real do banco (ex.: `odoo_steriliza`):

```bash
chmod +x scripts/pgvector_enable.sh
DB=<DB> bash scripts/pgvector_enable.sh
```

Resposta esperada:

```
 extname | extversion
---------+------------
 vector  | 0.7.x
```

## 4. Configurar Odoo

UI: **Configurações > Configurações Gerais > Assistente LLM**

| Campo | Valor |
|---|---|
| Provedor LLM | LM Studio / OpenAI-compatible (local) |
| URL base | `http://ollama:11434/v1` |
| Modelo | `qwen2.5:3b-instruct-q4_K_M` |
| Chave API | (vazio) |

Salvar.

> **Importante:** URL `http://ollama:11434/v1` funciona porque o container `web` do Odoo está na mesma rede do compose. NÃO usar `host.docker.internal` aqui.

## 5. Testar chat

Abrir Odoo → systray do LLM Assistant → enviar mensagem.

Esperado: resposta em ~10-30s (CPU). Primeira chamada é mais lenta (carrega modelo em RAM).

## Troubleshooting

**Connection refused do Odoo para Ollama**
- Confirmar mesma rede: `docker compose exec web getent hosts ollama` deve retornar IP.
- Limpar overrides antigos de `ODOO_LMSTUDIO_API_BASE` no `docker-compose.yml` ou env vars (têm prioridade sobre param do sistema).

**Modelo lento (>60s para resposta curta)**
- CPU sem AVX2: trocar pra modelo menor (`qwen2.5:1.5b-instruct-q4_K_M`).
- Verificar RAM livre: `free -h`. Se swap em uso, reduzir `OLLAMA_KEEP_ALIVE` ou subir RAM da VPS.

**`CREATE EXTENSION vector` falha**
- Confirmar imagem do db: `docker compose images db` deve mostrar `pgvector/pgvector:pg12`.
- Se mostrar `postgres:12`, override não foi aplicado — checar comando `-f docker-compose.ollama.yml`.

## Reverter

```bash
docker compose -f docker-compose.yml -f docker-compose.ollama.yml down
# volume ollama_models permanece; remover manualmente se quiser:
# docker volume rm odoo_engenapp_ollama_models
```

Para voltar ao `postgres:12` puro: subir só com `docker-compose.yml`. pgvector continua instalado no DB (extensão fica no schema), mas image base não terá os binários — `CREATE EXTENSION` futuro falha. Reverter extensão: `DROP EXTENSION vector;` antes de voltar.
