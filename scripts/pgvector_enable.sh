#!/usr/bin/env bash
# Ativa extensão pgvector no DB do Odoo.
#
# Uso:
#   DB=odoo_steriliza bash scripts/pgvector_enable.sh
set -euo pipefail

DB="${DB:-${POSTGRES_DB:-postgres}}"
USER_DB="${PGUSER:-odoo}"

echo ">> CREATE EXTENSION vector no DB=$DB"
docker compose exec -T db psql -U "$USER_DB" -d "$DB" -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo ">> Versão instalada:"
docker compose exec -T db psql -U "$USER_DB" -d "$DB" -c "SELECT extname, extversion FROM pg_extension WHERE extname='vector';"
