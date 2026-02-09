# Runbook

## Setup and local run
1. Install dependencies:
- API: `cd api && python -m venv .venv && source .venv/bin/activate && pip install -e .[dev]`
- Workers: `cd workers && python -m venv .venv && source .venv/bin/activate && pip install -e .[dev]`
- Web: `fnm use 24.13.0 && pnpm install --dir web`
2. Start local services:
- API: `cd api && uvicorn app.main:app --reload`
- Worker: `cd workers && python -m app.main`
- Web: `fnm use 24.13.0 && pnpm --dir web dev`
3. Run app locally: start API + web for browsing, then worker for job processing.

## Build/test/quality
1. Build: `python -m compileall api/app workers/app` and `fnm exec --using 24.13.0 pnpm --dir web build`
2. Test: `cd api && pytest` and `cd workers && pytest`
3. Lint: `cd api && ruff check app tests` and `cd workers && ruff check app tests` and `fnm exec --using 24.13.0 pnpm --dir web lint`
4. Typecheck: `cd api && mypy app` and `cd workers && mypy app` and `fnm exec --using 24.13.0 pnpm --dir web typecheck`
5. Required pre-finalization checks (fill with concrete commands): `bash scripts/agent-hygiene-check.sh --mode project`

## Database operations
1. Migration command: `DATABASE_URL=... bash scripts/apply_db_schema.sh`
2. Seed command: included in `scripts/apply_db_schema.sh` (`db/seeds/001_taxonomy.sql`)
3. Rollback/recovery: `UNCONFIRMED` (down migrations not implemented yet)
4. Local integration DB lifecycle:
- Start DB: `make db-up`
- Reset schema+seed: `make db-reset`
- Run API integration tests: `make test-integration`
- Stop DB: `make db-down`
5. Before running compose targets, verify Docker daemon availability (`docker info` or equivalent) to avoid socket connection failures.

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
9. Keep spec/roadmap references pointed at `docs/spec/` and `docs/roadmap/`; avoid relying on external handoff folders.
10. After doc migrations/imports, run a quick absolute-path scan before hygiene/CI (for example, check for machine-local home-directory prefixes).
