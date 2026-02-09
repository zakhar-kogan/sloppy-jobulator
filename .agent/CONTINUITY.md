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
Now: `extract` job completion now materializes `posting_candidates`, links candidate discoveries/evidence, projects baseline `postings`, and emits provenance events; DB-backed projection integration tests pass locally with OrbStack.
Next: Implement `D2` lease reaper + retry/dead-letter transitions, then finalize Supabase role metadata conventions + moderation endpoints.
Open Questions: exact production Supabase URL/key provisioning and human role metadata conventions are UNCONFIRMED.

## Done (recent)
- 2026-02-08 `[CODE]` Added local Postgres compose definition and make targets for DB lifecycle + integration test execution.
- 2026-02-08 `[CODE]` Expanded API integration tests to cover `/postings` DB-read path in addition to discovery/job flow.
- 2026-02-08 `[CODE]` Switched API app DB pool cleanup from deprecated `on_event` to lifespan teardown to stabilize integration test client lifecycle.
- 2026-02-08 `[CODE]` Added `scripts/reset_db.sh` and updated `scripts/apply_db_schema.sh` fallback + `ON_ERROR_STOP` behavior for host-without-psql workflows.
- 2026-02-08 `[TOOL]` Verified full local compose-backed integration run passes (`db-up -> db-reset -> test-integration -> db-down`).
- 2026-02-09 `[CODE]` Added `extract` job projection flow in API repository to materialize candidates/postings with candidate/posting provenance events.
- 2026-02-09 `[CODE]` Extended DB integration test coverage to assert discovery -> claimed job -> done result -> projected posting behavior.

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
