#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required"
  exit 1
fi

psql "$DATABASE_URL" -f db/migrations/0001_schema_v1.sql
psql "$DATABASE_URL" -f db/seeds/001_taxonomy.sql

echo "Schema and seed applied"
