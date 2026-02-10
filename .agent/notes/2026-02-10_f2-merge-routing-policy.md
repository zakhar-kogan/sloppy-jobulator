# Task Note: F2 merge-aware trust-policy routing

## Task
- Request: Continue from "what next?" and proceed with the next roadmap slice.
- Scope: Expand `F2` trust-policy routing to consume merge-policy outcomes with source-specific controls, add integration coverage, and capture project-mode state.
- Constraints: Keep diffs reviewable, preserve existing contracts, validate with repo-standard checks where available.

## Actions Taken
1. Added merge-aware routing logic in `api/app/services/repository.py` via `_resolve_merge_decision_routing` with defaults for `needs_review`, `auto_merged`, and `rejected`.
2. Added policy override support in `source_trust_policy.rules_json` for `merge_decision_actions`, `merge_decision_reasons`, and `moderation_routes`.
3. Ensured final candidate state is persisted after merge routing decisions, including fallback paths after blocked auto-merge attempts.
4. Added DB-backed integration tests for source-specific override behavior on dedupe `needs_review` and `rejected` outcomes.
5. Updated roadmap and agent continuity/execplan state for project-mode capture.

## What Went Wrong
1. Issue: Initial DB-backed test attempt failed inside sandbox.
- Root cause: sandbox denied localhost socket access for asyncpg.
- Early signal missed: first pytest run raised `PermissionError: [Errno 1] Operation not permitted` on DB connect.
- Prevention rule: for local Postgres integration tests, run with escalation immediately when sandbox connect failures appear.

2. Issue: `make lint` / `make typecheck` failed on host tooling path.
- Root cause: host `ruff` and `mypy` binaries are not installed globally.
- Early signal missed: Makefile assumes host-installed linters/typecheckers.
- Prevention rule: prefer `uv run --project ...` checks for touched Python paths when host tools are absent.

## What Went Right
1. Improvement: Merge outcome routing is now explicit and policy-driven instead of hardcoded per decision.
- Evidence (time/readability/performance/manageability/modularity): single helper centralizes decision-to-state mapping and reduces duplicated conditional logic in extract projection flow.
- Why it worked: keeping route resolution pure and localized made fallback handling (`auto_merged` -> `needs_review`) deterministic.

2. Improvement: Added focused DB integration tests that validate real policy behavior across merge decisions.
- Evidence (time/readability/performance/manageability/modularity): targeted suite (`2/2`) plus broader trust/dedupe subset (`8/8`) passed without touching unrelated contracts.
- Why it worked: tests reuse existing projection helper and assert both persisted state and provenance payload receipts.

## Reusable Learnings
1. Learning: Treat merge-policy outcomes as first-class inputs to trust-policy routing rather than post-hoc flags.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `PATTERNS.md`
- Why: applies to upcoming policy engines and keeps publish logic consistent across machine decisions.

2. Learning: Sandbox DB restrictions are recurrent for localhost integration tests in this environment.
- Promotion decision: `keep local`
- Promote to (if `promote now`): `helpers/`
- Why: helper already exists (`H-2026-02-10__db-integration-escalation`), so no new promotion needed.

## Receipts
- Commands run: `uv run --project api --extra dev ruff check api/app/services/repository.py api/tests/test_discovery_jobs_integration.py`; `uv run --project api --extra dev mypy api/app/services/repository.py`; `make db-up`; `make db-reset`; escalated `uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "override_needs_review_merge_route_for_source or override_rejected_merge_route_for_source"`; escalated `... -k "dedupe_policy or trust_policy"`; `make db-down`; `make lint`; `make typecheck`.
- Files changed: `api/app/services/repository.py`, `api/tests/test_discovery_jobs_integration.py`, `docs/roadmap/IMPLEMENTATION_PLAN_v1.2.md`, `.agent/CONTINUITY.md`, `.agent/execplans/active/EP-2026-02-08__bootstrap-foundation-v1.md`, `.agent/execplans/INDEX.md`, `.agent/notes/2026-02-10_f2-merge-routing-policy.md`.
- Tests/checks: targeted lint/typecheck passed via `uv`; new integration tests passed (`2/2` selected); broader dedupe/trust integration subset passed (`8/8` selected); `make lint` and `make typecheck` failed due missing host `ruff`/`mypy`.
