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
Now: `F2` trust-policy routing now consumes merge-policy outcomes with policy-configurable merge actions/reasons/moderation routes and explicit `rejected` handling.
Next: Expose/administer `source_trust_policy.rules_json` merge-routing keys and extend edge coverage for auto-merge-blocked conflict paths.
Open Questions: exact production Supabase URL/key provisioning and human role metadata conventions are UNCONFIRMED.

## Done (recent)
- 2026-02-10 `[CODE]` Added `dedupe.py` scorer v1 with deterministic precision-first confidence over strong signals (hash/URL), medium text similarity, and NER/contact-domain tie-breakers.
- 2026-02-10 `[CODE]` Wired scorer into extract projection so candidate risk flags/confidence now drive machine merge-policy outcomes (`auto_merged`, `needs_review`, `rejected`).
- 2026-02-10 `[CODE]` Added shared merge execution helper so manual moderator merges and machine auto-merges share consistent `candidate_merge_decisions` + provenance behavior.
- 2026-02-10 `[CODE]` Added auto-merge short-circuit to keep canonical posting ownership stable while archiving secondary candidates and retaining discovery/evidence links on the primary.
- 2026-02-10 `[CODE]` Added review-routing override so uncertain/conflicting dedupe outcomes force moderation queue state even when trust-policy would otherwise auto-publish.
- 2026-02-10 `[CODE]` Expanded `source_trust_policy` merge routing to apply policy-configurable `merge_decision_actions`/`merge_decision_reasons`/`moderation_routes` and default `rejected` handling.
- 2026-02-10 `[CODE]` Added DB-backed integration coverage for source-specific overrides on dedupe `needs_review` and `rejected` outcomes.

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
- 2026-02-10 `[TOOL]` `uv run --project api --extra dev ruff check api/app/services/repository.py api/tests/test_discovery_jobs_integration.py` and `uv run --project api --extra dev mypy api/app/services/repository.py` passed.
- 2026-02-10 `[TOOL]` `make db-up -> make db-reset -> (escalated) SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "override_needs_review_merge_route_for_source or override_rejected_merge_route_for_source" -> (escalated) ... -k "dedupe_policy or trust_policy" -> make db-down` passed (`2/2` selected, then `8/8` selected).
- 2026-02-10 `[TOOL]` `make lint` and `make typecheck` failed on host (`ruff`/`mypy` missing in PATH); equivalent `uv run --project api --extra dev` checks passed for touched API files.
