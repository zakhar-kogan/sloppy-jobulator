# Task Note: 2026-02-10 f2-policy-validation-surface

## Task
- Request: add strict `rules_json` merge-routing validation in repository write path, expand mixed trust + conflicting dedupe integration regressions, and update roadmap/admin-contract docs.
- Scope: `api/app/services/repository.py`, `api/tests/test_discovery_jobs_integration.py`, and `docs/roadmap/IMPLEMENTATION_PLAN_v1.2.md`.
- Constraints: keep trust-policy behavior backward-compatible for valid configurations, enforce validation at write-time, and keep DB-backed integration coverage deterministic.

## Actions Taken
1. Added `RepositoryValidationError` plus strict trust-policy validators in `PostgresRepository` for:
- allowed `merge_decision_actions` values,
- route-label format checks for `moderation_routes` and `default_moderation_route`,
- unknown-key rejection for top-level and merge-routing maps.
2. Added `upsert_source_trust_policy(...)` in repository and enforced strict validation before writing to `source_trust_policy`.
3. Routed integration policy upserts through repository write path and added new integration cases:
- mixed trust + conflicting hash signal (`semi_trusted` -> `needs_review`),
- mixed trust + rejected dedupe signal (`untrusted` -> `rejected`),
- negative write-path validation tests (unknown key, invalid action, invalid route label).
4. Updated roadmap `F2` status and next-step admin API contract references.

## What Went Wrong
1. Issue: sandboxed integration run failed even after DB container startup due localhost socket restrictions.
- Root cause: pytest/asyncpg needed local Postgres network access denied by sandbox policy.
- Early signal missed: initial test invocation was executed in sandbox without escalation.
- Prevention rule: when DB-backed tests are required in this environment, expect localhost socket denial and escalate immediately after the first permission failure.
- Promotion decision: `promote now`
- Promote to: `helpers/`
- Why: this failure mode is recurring and materially reduces retry churn when captured as a standard run pattern.

## What Went Right
1. Improvement: policy validation is now centralized in repository write path and exercised by integration helpers/tests.
- Evidence (time/readability/performance/manageability/modularity): one validation contract now governs all repository-level writes, and new regressions verify both happy-path and rejection-path behavior in DB-backed flow (`8/8` selected tests).
- Why it worked: moving writes through a single repository API eliminated divergent SQL helper behavior and made validation easy to test.
- Promotion decision: `promote now`
- Promote to: `PATTERNS.md`
- Why: centralizing mutable policy validation at repository boundary is reusable for upcoming admin policy CRUD surfaces.

2. Improvement: mixed trust + dedupe conflict coverage now extends beyond auto-merge fallback tests.
- Evidence (time/readability/performance/manageability/modularity): test suite now explicitly asserts `semi_trusted` conflict review routing and `untrusted` rejected routing with provenance expectations.
- Why it worked: existing `_create_projected_candidate_and_posting` helper was flexible enough to synthesize deterministic conflicting signals with minimal harness changes.
- Promotion decision: `pilot backlog`
- Why: high leverage for trust-policy evolution, but full admin API-level contract testing is still pending.

## Receipts
- Commands run:
  - `uv run --project api --extra dev ruff check api/app/services/repository.py api/tests/test_discovery_jobs_integration.py`
  - `uv run --project api --extra dev mypy api/app/services/repository.py`
  - `make db-up`
  - `make db-reset`
  - `(escalated) UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "mixed_trust or write_rejects_unknown_merge_routing_key or write_rejects_invalid_merge_action or write_rejects_invalid_route_label or trust_policy_can_override_needs_review_merge_route_for_source or trust_policy_can_override_rejected_merge_route_for_source or trust_policy_override_applies_when_auto_merge_fallbacks_to_needs_review"`
  - `make db-down`
  - `bash scripts/agent-hygiene-check.sh --mode project`
- Files changed:
  - `api/app/services/repository.py`
  - `api/tests/test_discovery_jobs_integration.py`
  - `docs/roadmap/IMPLEMENTATION_PLAN_v1.2.md`
  - `.agent/CONTINUITY.md`
  - `.agent/execplans/active/EP-2026-02-08__bootstrap-foundation-v1.md`
  - `.agent/notes/2026-02-10_f2-policy-validation-surface.md`
- Tests/checks:
  - Ruff passed for touched API files.
  - Mypy passed for touched repository file.
  - Targeted DB-backed integration selection passed (`8/8`).
  - Agent hygiene check passed (project mode).
