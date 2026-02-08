# Sloppy Jobulator

Public research opportunities aggregator. This repo contains a monorepo scaffold for:
- `api/` FastAPI control plane
- `workers/` Python job processors
- `web/` Next.js public catalogue + admin surfaces
- `db/` Postgres schema and migrations
- `handoff/` imported specification and implementation plan

## Current Phase

Initial foundation implementation is in progress (Phase 1 from `handoff/IMPLEMENTATION_PLAN_v1.2.md`).

## Quick Start

1. Review specs:

```bash
ls handoff
```

2. Run API locally:

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

3. Run worker scaffold locally:

```bash
cd workers
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m app.main
```

4. Run web locally:

```bash
cd web
npm install
npm run dev
```

## Project Commands

```bash
make build
make test
make lint
make typecheck
```

## Notes

- Schema baseline lives in `db/schema_v1.sql`.
- First migration is `db/migrations/0001_schema_v1.sql`.
- Handoff source docs were copied into local `handoff/` for traceability.
