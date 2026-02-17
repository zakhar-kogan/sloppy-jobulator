#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required"
  exit 1
fi

apply_with_host_psql() {
  psql -v ON_ERROR_STOP=1 "$DATABASE_URL" -f db/migrations/0001_schema_v1.sql
  for seed_file in db/seeds/*.sql; do
    psql -v ON_ERROR_STOP=1 "$DATABASE_URL" -f "$seed_file"
  done
}

apply_with_compose_psql() {
  local db_user db_name

  if [[ "$DATABASE_URL" =~ postgresql://([^:/]+):[^@]+@[^/]+/([^?]+) ]]; then
    db_user="${BASH_REMATCH[1]}"
    db_name="${BASH_REMATCH[2]}"
  else
    echo "Could not parse DATABASE_URL for docker compose fallback."
    exit 1
  fi

  cat db/migrations/0001_schema_v1.sql | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U "$db_user" -d "$db_name"
  for seed_file in db/seeds/*.sql; do
    cat "$seed_file" | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U "$db_user" -d "$db_name"
  done
}

if command -v psql >/dev/null 2>&1; then
  apply_with_host_psql
elif command -v docker >/dev/null 2>&1 && docker compose ps postgres >/dev/null 2>&1; then
  echo "psql not found on host; using docker compose postgres service for schema apply."
  apply_with_compose_psql
else
  echo "Neither host psql nor a running docker compose postgres service is available."
  exit 1
fi

echo "Schema and seed applied"
