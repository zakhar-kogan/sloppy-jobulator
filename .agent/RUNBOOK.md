# Runbook

## Setup and local run
1. Install dependencies:
- API: `cd api && python -m venv .venv && source .venv/bin/activate && pip install -e .[dev]`
- Workers: `cd workers && python -m venv .venv && source .venv/bin/activate && pip install -e .[dev]`
- Web: `cd web && npm install`
2. Start local services:
- API: `cd api && uvicorn app.main:app --reload`
- Worker: `cd workers && python -m app.main`
- Web: `cd web && npm run dev`
3. Run app locally: start API + web for browsing, then worker for job processing.

## Build/test/quality
1. Build: `python -m compileall api/app workers/app` and `cd web && npm run build`
2. Test: `cd api && pytest` and `cd workers && pytest`
3. Lint: `cd api && ruff check app tests` and `cd workers && ruff check app tests` and `cd web && npm run lint`
4. Typecheck: `cd api && mypy app` and `cd workers && mypy app` and `cd web && npm run typecheck`
5. Required pre-finalization checks (fill with concrete commands): `bash scripts/agent-hygiene-check.sh --mode project`

## Database operations
1. Migration command: `DATABASE_URL=... bash scripts/apply_db_schema.sh`
2. Seed command: included in `scripts/apply_db_schema.sh` (`db/seeds/001_taxonomy.sql`)
3. Rollback/recovery: `UNCONFIRMED` (down migrations not implemented yet)

## Incident basics
1. Health check endpoint/command: `GET /healthz` on API.
2. Log query path: `UNCONFIRMED` (Cloud Logging filters pending infra setup).
3. Rollback command/path: `UNCONFIRMED` (deployment automation pending).

## Agentic framework maintenance
1. Set workflow mode explicitly:
- Template repo: `--mode template` (sanitized scaffold only).
- Downstream project repo: `--mode project` (full task-state capture).
2. For substantial tasks, run a balanced review:
- What went wrong, why, prevention?
- What went right, measurable improvement, reusable or not?
3. Triage each item as `promote now | pilot backlog | keep local`.
4. In `project` mode, update notes/helpers/continuity and promote high-leverage items.
5. In `template` mode, do not record live task state; only improve reusable template policy/docs/scripts.
6. Weekly hygiene: prune stale notes, deduplicate conflicting guidance, and update `UNCONFIRMED` commands when known.
7. Run contract checks: `bash scripts/agent-hygiene-check.sh --mode template|project`.
8. Run weekly maintenance review: `bash scripts/agent-weekly-review.sh --mode template|project`.
9. If work references `/handoff`, first verify `handoff/` exists in the repo; if missing, import the agreed source before coding.
