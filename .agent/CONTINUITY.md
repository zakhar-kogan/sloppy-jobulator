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
Now: `G2` baseline landed with scheduled freshness enqueue (`/jobs/enqueue-freshness`), worker `check_freshness` execution, and automated dead-letter downgrade/archive transitions plus provenance coverage.
Next: Implement `E3` dedupe scorer v1 and connect confidence/risk outputs to `E4` merge policy routing.
Open Questions: exact production Supabase URL/key provisioning and human role metadata conventions are UNCONFIRMED.

## Done (recent)
- 2026-02-10 `[CODE]` Added `POST /jobs/enqueue-freshness` with DB-backed due-posting scheduler and duplicate suppression for pending freshness jobs.
- 2026-02-10 `[CODE]` Added `check_freshness` result/dead-letter handling in repository to apply deterministic machine-driven posting transitions (`active->stale`, `stale->archived`) with candidate-state sync + provenance events.
- 2026-02-10 `[CODE]` Added worker freshness automation loop (`enqueue_freshness_jobs`) and `check_freshness` evaluator dispatch with configurable stale/archive thresholds.
- 2026-02-10 `[CODE]` Added DB-backed integration coverage for freshness enqueue + machine transitions and retry-exhausted downgrade path.
- 2026-02-10 `[CODE]` Added `PATCH /postings/{posting_id}` with moderated human auth and posting lifecycle payload contract.
- 2026-02-10 `[CODE]` Added DB-backed integration coverage for posting lifecycle path (`active -> stale -> archived -> active`) and invalid transition conflict (`closed -> active`).
- 2026-02-09 `[CODE]` Added F2 trust-policy publication routing via `source_trust_policy` with provenance event writes (`trust_policy_applied`).

## Working set
- 2026-02-08 `[ASSUMPTION]` Target stack remains Next.js + FastAPI + Supabase + Cloud Run per spec.
- 2026-02-08 `[CODE]` Node toolchain standardized on `fnm` + `pnpm` with root `.node-version` and `web/pnpm-lock.yaml`.
- 2026-02-08 `[CODE]` Local API `make test` keeps integration tests skipped unless DB URL env vars are set (while `make test-integration` enforces DB-backed run).

## Decisions
- 2026-02-08 `[CODE]` D-001 through D-004 active in `.agent/DECISIONS.md`.

## Receipts
- 2026-02-09 `[TOOL]` `make db-up -> make db-reset -> SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -> make db-down` passed (`17/17`, includes trust-policy routing coverage).
- 2026-02-09 `[TOOL]` `uv run --project api --extra dev pytest api/tests --ignore=api/tests/test_discovery_jobs_integration.py` passed (`13/13`, includes bootstrap-script tests).
- 2026-02-09 `[TOOL]` `gh run list --branch main --limit 6` confirms post-merge `main` checks passed (`CI` run `21835425786`, `Agent Hygiene` run `21835425797`).
- 2026-02-10 `[TOOL]` `make db-up -> make db-reset -> SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "posting_lifecycle_patch or moderation_candidate_state_transitions_update_posting_status" -> make db-down` passed (`3/3` selected).
- 2026-02-10 `[TOOL]` `uv run --project api --extra dev pytest api/tests --ignore=api/tests/test_discovery_jobs_integration.py` passed (`15/15`, includes posting patch authz tests).
- 2026-02-10 `[TOOL]` `uv run --project api --extra dev ruff check api/app api/tests && uv run --project api --extra dev mypy api/app` passed.
- 2026-02-10 `[TOOL]` `uv run --project workers --extra dev pytest workers/tests -q` passed (`6/6`, includes freshness evaluator coverage).
- 2026-02-10 `[TOOL]` `UV_CACHE_DIR=/tmp/uv-cache uv run --project api --extra dev ruff check ...` and `UV_CACHE_DIR=/tmp/uv-cache uv run --project workers --extra dev ruff check ...` passed for changed freshness files.
- 2026-02-10 `[TOOL]` `UV_CACHE_DIR=/tmp/uv-cache uv run --project api --extra dev mypy api/app` and `UV_CACHE_DIR=/tmp/uv-cache uv run --project workers --extra dev mypy workers/app` passed.
- 2026-02-10 `[TOOL]` `make db-up -> make db-reset -> SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "enqueue_freshness_jobs or freshness_dead_letter" -> make db-down` passed (`2/2` selected).
