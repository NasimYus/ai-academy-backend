#!/usr/bin/env bash
# Reset the local dev database: drop the public schema and re-run all migrations
# from scratch. Use when the schema drifted from the models (e.g. a stale `users`
# table). DESTRUCTIVE — wipes all data in the target database.
#
# Usage:
#   ./scripts/reset_db.sh                 # uses DATABASE_URL or the config default
#   DATABASE_URL=postgresql+asyncpg://u:p@host:5432/db ./scripts/reset_db.sh
set -euo pipefail

cd "$(dirname "$0")/.."

# Default mirrors app/core/config.py. psql needs the plain libpq URL, so strip the
# SQLAlchemy "+asyncpg" driver suffix if present.
RAW_URL="${DATABASE_URL:-postgresql+asyncpg://aiacademy:aiacademy@localhost:5432/aiacademy}"
PSQL_URL="${RAW_URL/+asyncpg/}"

echo "Target: ${PSQL_URL}"
read -r -p "Drop schema 'public' and re-run migrations? This wipes all data. [y/N] " ans
case "${ans}" in
  y | Y | yes | YES) ;;
  *) echo "Aborted."; exit 1 ;;
esac

echo "==> Dropping and recreating schema 'public'"
psql "${PSQL_URL}" -v ON_ERROR_STOP=1 -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo "==> Applying migrations"
uv run alembic upgrade head

echo "==> Current revision"
uv run alembic current

echo "Done. Database reset to a clean, fully-migrated state."
