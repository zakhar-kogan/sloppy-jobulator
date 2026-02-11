#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required"
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "psql is required for migration safety gate"
  exit 1
fi

bash scripts/apply_db_schema.sh

psql -v ON_ERROR_STOP=1 "$DATABASE_URL" <<'SQL'
do $$
begin
  if to_regclass('public.discoveries') is null then
    raise exception 'discoveries table missing after migration';
  end if;
  if to_regclass('public.jobs') is null then
    raise exception 'jobs table missing after migration';
  end if;
  if to_regclass('public.postings') is null then
    raise exception 'postings table missing after migration';
  end if;
end;
$$;
SQL

echo "Migration safety gate passed"
