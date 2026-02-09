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
Now: `A3/F2` baseline is active: role bootstrap SQL automation is documented, and extract projection now resolves `source_trust_policy` to route publish outcomes (`published` vs `needs_review`) with integration coverage.
Next: Open PR and verify real CI reports `api-fast` and `api-integration-db` as separate checks under branch protection.
Open Questions: exact production Supabase URL/key provisioning is UNCONFIRMED.

## Done (recent)
- 2026-02-09 `[CODE]` Enabled GitHub `main` branch protection required checks: `api-fast`, `api-integration-db`, `workers`, `web`, `validate-agent-contract`.
- 2026-02-09 `[CODE]` Added `F2` trust-policy publish path in extract projection via `source_trust_policy` resolution with provenance events (`trust_policy_applied`).
- 2026-02-09 `[CODE]` Added DB-backed integration tests for trust-policy behavior (trusted confidence gate, semi-trusted auto-publish, untrusted moderation, source-key override).
- 2026-02-09 `[CODE]` Replaced placeholder bootstrap script with deterministic Supabase role/provenance SQL generation (`scripts/bootstrap_admin.py --user-id|--email --role`).
- 2026-02-09 `[CODE]` Split CI API checks into `api-fast` and `api-integration-db`, and documented required branch checks in `README.md`.
- 2026-02-09 `[CODE]` Added moderation merge + override workflows (`POST /candidates/{id}/merge|override`) with candidate/posting audit event retrieval.
- 2026-02-09 `[CODE]` Hardened postings list semantics for whitespace-only filters, case-insensitive tag filtering, deterministic sort tie-breaks, and null-last `deadline/published_at` ordering with DB-backed integration tests.

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
- 2026-02-09 `[TOOL]` `uv run --project api --extra dev pytest api/tests/test_candidates_authz.py api/tests/test_health.py` passed (`11/11`, includes merge/override authz coverage).
- 2026-02-09 `[TOOL]` `SJ_DATABASE_URL=... SJ_JOB_RETRY_BASE_SECONDS=0 uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py` passed (`12/12`, includes moderation merge/conflict/override + audit coverage).
- 2026-02-09 `[TOOL]` `SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "postings_list_reads_from_database or postings_filters_sort_pagination_and_detail or postings_edge_query_semantics_and_deterministic_tie_breaks"` passed (`3/3`).
- 2026-02-09 `[TOOL]` `make db-up -> make db-reset -> SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -> make db-down` passed (`13/13`).
- 2026-02-09 `[TOOL]` `uv run --project api --extra dev pytest api/tests --ignore=api/tests/test_discovery_jobs_integration.py` passed (`11/11`).
- 2026-02-09 `[TOOL]` `uv run --project api --extra dev pytest api/tests --ignore=api/tests/test_discovery_jobs_integration.py` passed (`13/13`, includes bootstrap-script tests).
- 2026-02-09 `[TOOL]` `make db-up -> make db-reset -> SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -> make db-down` passed (`17/17`, includes trust-policy routing coverage).
