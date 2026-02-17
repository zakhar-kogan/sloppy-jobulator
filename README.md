# Sloppy Jobulator

Public research opportunities aggregator. This repo contains a monorepo scaffold for:
- `api/` FastAPI control plane
- `workers/` Python job processors
- `web/` Next.js public catalogue + admin surfaces
- `db/` Postgres schema and migrations
- `docs/spec/` product specification
- `docs/roadmap/` implementation roadmap

## Current Phase

Phase 3 baseline implementation is in progress (`A3/F2/F3/G2` baseline landed; `E3` dedupe scorer + `E4` merge-policy automation remain on the critical path).

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
- `web-e2e-live`
- `migration-safety`
- `validate-agent-contract` (from `Agent Hygiene` workflow)

This keeps fast checks and DB-backed integration checks as separate required gates.

On `push` to `main`, CI also runs `deploy-readiness-gate` after all quality + migration gates pass.
When that CI run succeeds, the `Deploy` workflow now auto-runs for staging from the same commit SHA.
`Deploy` can still be run manually via `workflow_dispatch` for controlled/staged rollout options.

## Human Role Bootstrap (A3)

Generate deterministic SQL for Supabase role assignment + provenance audit:

```bash
python scripts/bootstrap_admin.py --user-id 00000000-0000-0000-0000-000000000000 --role admin
```

Email-based targeting is also supported:

```bash
python scripts/bootstrap_admin.py --email admin@example.edu --role moderator
```

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

## OTel Runtime Config (J1)

API (`SJ_` prefix) and workers (`SJ_WORKER_` prefix) support:
- `OTEL_ENABLED` (default `true`)
- `OTEL_SERVICE_NAME`
- `OTEL_EXPORTER_OTLP_ENDPOINT` (or standard `OTEL_EXPORTER_OTLP_ENDPOINT` env)
- `OTEL_EXPORTER_OTLP_HEADERS` (`key=value,key2=value2`)
- `OTEL_TRACE_SAMPLE_RATIO` (default `1.0`)
- `OTEL_LOG_CORRELATION` (default `true`)

J2 dashboard and alert artifacts live under `docs/observability/`.
Environment binding checklist/examples (service labels, notification channels, OTLP endpoints) live under `docs/observability/ENVIRONMENT_BINDINGS.md`.

## Redirect Resolution Rollout (E2 v0)

Redirect-resolution enqueue is available behind a feature flag:
- `SJ_ENABLE_REDIRECT_RESOLUTION_JOBS` (default `false`).

When enabled, discovery ingest enqueues `resolve_url_redirects` jobs in addition to `extract`, and completed redirect jobs can refresh discovery canonical URL/hash and enqueue a follow-up `extract` replay if canonical fields changed.
