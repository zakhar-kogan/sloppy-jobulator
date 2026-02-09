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
6. CI gate split (`M1 + L1`):
- Fast lane: `api-fast`, `workers`, `web`.
- DB-backed integration lane: `api-integration-db` (runs `api/tests/test_discovery_jobs_integration.py` with Postgres + schema apply).
- Branch protection should require: `api-fast`, `api-integration-db`, `workers`, `web`, and `validate-agent-contract`.

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

## Supabase human role provisioning (B3)
1. Source of truth for elevated roles is Supabase `app_metadata` only; `user_metadata` must not grant `moderator`/`admin`.
2. API claim resolution order is:
- `app_metadata.role`
- `app_metadata.sj_role`
- first recognized value in `app_metadata.roles[]`
3. Allowed role values: `user`, `moderator`, `admin` (unknown values downgrade to `user`).
4. Example SQL (run in Supabase SQL editor with admin privileges):
- Set moderator role:
```sql
update auth.users
set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) || jsonb_build_object('role', 'moderator')
where id = '00000000-0000-0000-0000-000000000000'::uuid;
```
- Set admin role:
```sql
update auth.users
set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) || jsonb_build_object('role', 'admin')
where id = '00000000-0000-0000-0000-000000000000'::uuid;
```
5. Verification query:
```sql
select id, raw_app_meta_data
from auth.users
where id = '00000000-0000-0000-0000-000000000000'::uuid;
```
6. After claim updates, refresh/re-authenticate the session so new JWT claims propagate to API calls.

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
