# Task Note: E3 dedupe scorer + E4 routing

## Task
- Request: Implement `E3` and wire it into `E4` merge-policy routing.
- Scope: API repository dedupe scoring, merge decision persistence/application, tests, and project-mode status capture docs.
- Constraints: Precision-first merge policy, deterministic confidence/risk output, no host package installs.

## Actions Taken
1. Added scorer module `api/app/services/dedupe.py` with deterministic signal weighting and decision thresholds (`auto_merged` / `needs_review` / `rejected`).
2. Integrated scorer into `PostgresRepository._materialize_extract_projection` and wired machine merge decisions into candidate state/posting routing + provenance payloads.
3. Refactored manual merge flow to shared merge internals so manual and machine merges write `candidate_merge_decisions` consistently.
4. Added unit tests for scorer behavior and DB-backed integration tests for auto-merge/review routing.
5. Updated roadmap, continuity, and active execplan tracking entries.

## What Went Wrong
1. Issue: Initial DB-backed integration test run failed in sandbox.
- Root cause: sandbox blocked localhost socket access to Postgres for asyncpg.
- Early signal missed: first run failed with `PermissionError: [Errno 1] Operation not permitted` on socket connect.
- Prevention rule: for DB-backed integration tests in this environment, immediately rerun with escalated permissions and keep `UV_CACHE_DIR=/tmp/uv-cache`.

## What Went Right
1. Improvement: Extracted scorer logic to a dedicated module instead of embedding it in repository methods.
- Evidence (time/readability/performance/manageability/modularity): scorer unit tests run in ~0.01s and repository integration diff stayed reviewable.
- Why it worked: pure-function scoring + typed snapshots allowed deterministic policy behavior without DB coupling.
2. Improvement: Unified merge execution path for human and machine flows.
- Evidence (time/readability/performance/manageability/modularity): reduced duplicate merge SQL/provenance logic and enabled machine auto-merge with existing moderation semantics.
- Why it worked: single helper (`_apply_candidate_merge`) centralized invariants and audit writes.

## Reusable Learnings
1. Learning: When adding machine decision engines, keep score computation pure and keep side effects (DB updates/provenance) in repository orchestration.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `PATTERNS.md`
- Why: reusable for future policy engines (trust-policy expansion, classifier routing, moderation automation).
2. Learning: Local DB integration tests may require escalation in sandboxed environments even when Docker is running.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `helpers/`
- Why: recurrent workflow failure mode; a helper entry prevents repeated trial-and-error.

## Receipts
- Commands run: `uv run --project api --extra dev ruff check ...`, `uv run --project api --extra dev mypy api/app`, `uv run --project api --extra dev pytest api/tests/test_dedupe_scorer.py -q`, `make db-up`, `make db-reset`, escalated `uv run ... pytest api/tests/test_discovery_jobs_integration.py -k "dedupe_policy_auto_merges_high_confidence_duplicate_candidate or dedupe_policy_routes_uncertain_match_to_review_queue"`, `make db-down`, `bash scripts/agent-hygiene-check.sh --mode project`.
- Files changed: `api/app/services/dedupe.py`, `api/app/services/repository.py`, `api/tests/test_dedupe_scorer.py`, `api/tests/test_discovery_jobs_integration.py`, `docs/roadmap/IMPLEMENTATION_PLAN_v1.2.md`, `.agent/CONTINUITY.md`, `.agent/execplans/active/EP-2026-02-08__bootstrap-foundation-v1.md`, `.agent/execplans/INDEX.md`.
- Tests/checks: scorer unit tests passed; targeted integration tests passed (`2/2` selected); lint/typecheck/hygiene passed.
