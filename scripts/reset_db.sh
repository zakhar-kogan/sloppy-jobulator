#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required"
  exit 1
fi

run_reset_host() {
  psql -v ON_ERROR_STOP=1 "$DATABASE_URL" -c "drop schema if exists public cascade; create schema public;"
}

run_reset_compose() {
  local db_user db_name

  if [[ "$DATABASE_URL" =~ postgresql://([^:/]+):[^@]+@[^/]+/([^?]+) ]]; then
    db_user="${BASH_REMATCH[1]}"
    db_name="${BASH_REMATCH[2]}"
  else
    echo "Could not parse DATABASE_URL for docker compose fallback."
    exit 1
  fi

  echo "drop schema if exists public cascade; create schema public;" \
    | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U "$db_user" -d "$db_name"
}

if command -v psql >/dev/null 2>&1; then
  run_reset_host
elif command -v docker >/dev/null 2>&1 && docker compose ps postgres >/dev/null 2>&1; then
  echo "psql not found on host; using docker compose postgres service for schema reset."
  run_reset_compose
else
  echo "Neither host psql nor a running docker compose postgres service is available."
  exit 1
fi

DATABASE_URL="$DATABASE_URL" bash scripts/apply_db_schema.sh

echo "Database reset complete"
