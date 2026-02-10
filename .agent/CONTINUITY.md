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
Now: `E3+E4` baseline landed with deterministic dedupe scoring, machine merge-policy decisions, auto-merge for high-confidence matches, and review-queue routing for uncertain/conflicting candidates.
Next: Expand `F2` trust-policy automation to consume richer merge-policy outcomes and source-specific moderation routing rules.
Open Questions: exact production Supabase URL/key provisioning and human role metadata conventions are UNCONFIRMED.

## Done (recent)
- 2026-02-10 `[CODE]` Added `dedupe.py` scorer v1 with deterministic precision-first confidence over strong signals (hash/URL), medium text similarity, and NER/contact-domain tie-breakers.
- 2026-02-10 `[CODE]` Wired scorer into extract projection so candidate risk flags/confidence now drive machine merge-policy outcomes (`auto_merged`, `needs_review`, `rejected`).
- 2026-02-10 `[CODE]` Added shared merge execution helper so manual moderator merges and machine auto-merges share consistent `candidate_merge_decisions` + provenance behavior.
- 2026-02-10 `[CODE]` Added auto-merge short-circuit to keep canonical posting ownership stable while archiving secondary candidates and retaining discovery/evidence links on the primary.
- 2026-02-10 `[CODE]` Added review-routing override so uncertain/conflicting dedupe outcomes force moderation queue state even when trust-policy would otherwise auto-publish.
- 2026-02-10 `[CODE]` Added unit coverage for dedupe scorer thresholds/conflict guards and DB-backed integration coverage for machine auto-merge + review-queue routing.
- 2026-02-10 `[CODE]` Maintained existing trust-policy event contract while extending payload receipts with merge-policy decision metadata.

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
- 2026-02-10 `[TOOL]` `uv run --project api --extra dev pytest api/tests/test_dedupe_scorer.py -q` passed (`4/4`).
- 2026-02-10 `[TOOL]` `uv run --project api --extra dev ruff check api/app/services/repository.py api/app/services/dedupe.py api/tests/test_dedupe_scorer.py api/tests/test_discovery_jobs_integration.py` and `uv run --project api --extra dev mypy api/app` passed.
- 2026-02-10 `[TOOL]` `make db-up -> make db-reset -> UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "dedupe_policy_auto_merges_high_confidence_duplicate_candidate or dedupe_policy_routes_uncertain_match_to_review_queue" -> make db-down` passed (`2/2` selected).
- 2026-02-10 `[TOOL]` `bash scripts/agent-hygiene-check.sh --mode project` passed.
