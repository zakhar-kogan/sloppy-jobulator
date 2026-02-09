# Continuity Ledger

Facts only. No transcripts. If unknown, write `UNCONFIRMED`.
Each entry must include date and provenance tag: `[USER]`, `[CODE]`, `[TOOL]`, `[ASSUMPTION]`.
In `project` mode, update this file whenever Goal/Now/Next/Decisions materially change.
In `template` mode, keep this file as scaffold-only.

## Size caps
- Snapshot: <= 25 non-empty lines.
- Done (recent): <= 7 bullets.
- Working set: <= 12 bullets.
- Receipts: <= 20 bullets (keep recent, compress older items).

## Snapshot

Goal: Ship Phase 1 baseline with DB-backed API persistence/auth, worker compatibility, and CI quality gates.
Now: `D2` is implemented: API supports expired-lease requeue + bounded retry/dead-letter transitions, workers trigger lease reaping, and DB-backed integration tests cover both paths.
Next: Finalize Supabase role metadata conventions and ship first moderation endpoints (`GET /candidates`, `PATCH /candidates/{id}`), then harden public postings read contracts.
Open Questions: exact production Supabase URL/key provisioning and human role metadata conventions are UNCONFIRMED.

## Done (recent)
- 2026-02-08 `[CODE]` Added local Postgres compose workflow + reset/apply script fallbacks (`make db-up/reset/test-integration/db-down`) for host-without-psql environments.
- 2026-02-08 `[CODE]` Switched API DB pool cleanup to lifespan teardown for stable integration test lifecycle.
- 2026-02-08 `[CODE]` Extended API integration coverage to `/postings` DB-read path.
- 2026-02-09 `[CODE]` Added `extract` result projection into candidates/postings with provenance writes.
- 2026-02-09 `[CODE]` Extended integration coverage to assert discovery -> claimed job -> done result -> projected posting flow.
- 2026-02-09 `[CODE]` Added D2 API reliability transitions: lease reaper endpoint + bounded retry/dead-letter resolution for failed results.
- 2026-02-09 `[CODE]` Updated worker loop to periodically trigger lease reaping and submit `failed` job results on execution exceptions.

## Working set
- 2026-02-08 `[ASSUMPTION]` Target stack remains Next.js + FastAPI + Supabase + Cloud Run per spec.
- 2026-02-08 `[CODE]` Node toolchain standardized on `fnm` + `pnpm` with root `.node-version` and `web/pnpm-lock.yaml`.
- 2026-02-08 `[CODE]` Local API `make test` keeps integration tests skipped unless DB URL env vars are set (while `make test-integration` enforces DB-backed run).

## Decisions
- 2026-02-08 `[CODE]` D-001 through D-004 active in `.agent/DECISIONS.md`.

## Receipts
- 2026-02-08 `[TOOL]` `make db-up` succeeded after OrbStack start (requires escalated sandbox access to Docker socket).
- 2026-02-08 `[TOOL]` `make db-reset` now works without host `psql` via compose fallback (`scripts/reset_db.sh` + `scripts/apply_db_schema.sh`).
- 2026-02-08 `[TOOL]` `make test-integration` passed with 3/3 integration tests against local Postgres container.
- 2026-02-08 `[TOOL]` `make lint && make typecheck && make test && make build` and `bash scripts/agent-hygiene-check.sh --mode project` passed.
- 2026-02-09 `[TOOL]` `uv run --project api --extra dev ruff check ...` and `uv run --project api --extra dev mypy api/app/services/repository.py` passed.
- 2026-02-09 `[TOOL]` `make db-up -> make db-reset -> SJ_DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -> make db-down` passed (3/3 integration tests).
- 2026-02-09 `[TOOL]` `uv run --project workers --extra dev pytest workers/tests` passed (`2/2`).
- 2026-02-09 `[TOOL]` `SJ_DATABASE_URL=... SJ_JOB_RETRY_BASE_SECONDS=0 uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py` passed (`5/5`, includes D2 cases).
