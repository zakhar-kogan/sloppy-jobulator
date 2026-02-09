# Sloppy Jobulator

Public research opportunities aggregator. This repo contains a monorepo scaffold for:
- `api/` FastAPI control plane
- `workers/` Python job processors
- `web/` Next.js public catalogue + admin surfaces
- `db/` Postgres schema and migrations
- `docs/spec/` product specification
- `docs/roadmap/` implementation roadmap

## Current Phase

Initial foundation implementation is in progress (Phase 1 from `docs/roadmap/IMPLEMENTATION_PLAN_v1.2.md`).

## Quick Start

1. Review specs:

```bash
ls docs/spec docs/roadmap
```

2. Apply schema and seed:

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sloppy_jobulator \
bash scripts/apply_db_schema.sh
```

3. Run API locally:

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
export SJ_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sloppy_jobulator
# Required for human-authenticated routes:
# export SJ_SUPABASE_URL=https://<project-ref>.supabase.co
# export SJ_SUPABASE_ANON_KEY=<anon-key>
uvicorn app.main:app --reload
```

4. Run worker scaffold locally:

```bash
cd workers
python -m venv .venv
source .venv/bin/activate
pip install -e .
export SJ_WORKER_API_KEY=local-processor-key
python -m app.main
```

5. Run web locally:

```bash
fnm use 24.13.0
pnpm install --dir web
pnpm --dir web dev
```

## Project Commands

```bash
make build
make test
make test-integration
make lint
make typecheck
```

## CI Required Checks (Branch Protection)

Configure branch protection to require these CI jobs:
- `api-fast`
- `api-integration-db`
- `workers`
- `web`
- `validate-agent-contract` (from `Agent Hygiene` workflow)

This keeps fast checks and DB-backed integration checks as separate required gates.

## Local Postgres for Integration Tests

```bash
make db-up
make db-reset
make test-integration
make db-down
```

By default these targets use `postgresql://postgres:postgres@localhost:5432/sloppy_jobulator`.
Override with `DB_URL=...` when needed.
`make db-reset` drops/recreates `public` schema, then reapplies migration + seed.

## Notes

- Schema baseline lives in `db/schema_v1.sql`.
- First migration is `db/migrations/0001_schema_v1.sql`.
- Dev machine credentials are seeded in `db/seeds/001_taxonomy.sql`.
- Node workflows use `fnm` + `pnpm` (`fnm use 24.13.0`).
