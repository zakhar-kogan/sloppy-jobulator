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
Now: PR #1 (`codex/a3-f2-bootstrap-policy`) merged to `main`; A3 bootstrap-role script hardening and F2 trust-policy publication routing landed with required CI checks passing.
Next: Implement `F3` posting lifecycle transitions, then `G2` freshness checker jobs.
Open Questions: exact production Supabase URL/key provisioning and human role metadata conventions are UNCONFIRMED.

## Done (recent)
- 2026-02-09 `[CODE]` Merged PR #1 (`codex/a3-f2-bootstrap-policy`) into `main`.
- 2026-02-09 `[CODE]` Added deterministic Supabase role bootstrap SQL generator (`scripts/bootstrap_admin.py --user-id|--email --role`) and tests.
- 2026-02-09 `[CODE]` Added F2 trust-policy publication routing via `source_trust_policy` with provenance event writes (`trust_policy_applied`).
- 2026-02-09 `[CODE]` Added DB-backed integration coverage for trusted/semi-trusted/untrusted publish routing and source-key policy override.
- 2026-02-09 `[CODE]` Split CI API checks into `api-fast` and `api-integration-db`, then enforced required checks via branch protection.
- 2026-02-09 `[CODE]` Branch `codex/a3-f2-bootstrap-policy` deleted locally and on `origin` after merge.
- 2026-02-09 `[CODE]` Branch-check names and required CI gate guidance documented in `README.md`.

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
- 2026-02-09 `[TOOL]` `gh run list --branch main --limit 6` confirms post-merge `main` checks passed (`CI` run `21835425786`, `Agent Hygiene` run `21835425797`).
