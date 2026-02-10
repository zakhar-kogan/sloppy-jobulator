# Task Note: 2026-02-10 f2-policy-audit-events

## Task
- Request: proceed with the next `F2` step by adding provenance/audit events for admin trust-policy writes/toggles.
- Scope: repository trust-policy write/toggle methods, admin route actor propagation, integration assertions, and roadmap/capture updates.
- Constraints: keep repository validation as single source of truth and preserve deterministic DB-backed test behavior.

## Actions Taken
1. Extended repository write APIs with actor context:
- `upsert_source_trust_policy(..., actor_user_id=...)`
- `set_source_trust_policy_enabled(..., actor_user_id=...)`
2. Added repository helper `_record_source_trust_policy_event(...)` and emitted:
- `policy_upserted` for admin `PUT`
- `policy_enabled_changed` for admin `PATCH`
3. Updated admin routes to pass authenticated human actor IDs into repository write/toggle calls.
4. Expanded admin integration test to assert provenance payload fields (`operation`, `previous_enabled`, `enabled`) and actor attribution.
5. Updated roadmap F2 status/next steps to reflect completed audit-event implementation.

## What Went Wrong
1. Issue: initial DB-backed selector run attempted inside sandbox and failed with localhost socket permission errors.
- Root cause: asyncpg localhost access blocked in sandbox.
- Early signal missed: first invocation was non-escalated despite recurring pattern.
- Prevention rule: run DB-backed selectors with `UV_CACHE_DIR=/tmp/uv-cache`; if localhost permission fails, rerun immediately with escalation.
- Promotion decision: `promote now`
- Promote to: `helpers/`
- Why: repeated across F2 tasks and directly reduces validation turnaround time.

## What Went Right
1. Improvement: policy-change auditability is now end-to-end from admin API to persisted provenance with actor attribution.
- Evidence (time/readability/performance/manageability/modularity): write/toggle events are produced in repository transaction scope and verified via integration assertions without adding route-layer SQL.
- Why it worked: reusing repository as the only mutable policy boundary kept audit insertion centralized and predictable.
- Promotion decision: `promote now`
- Promote to: `PATTERNS.md`
- Why: transactional audit write pattern is reusable for future admin configuration surfaces.

2. Improvement: admin API contract still passes both strict validation and new audit expectations.
- Evidence (time/readability/performance/manageability/modularity): targeted selector stayed green (`7/7`) after audit wiring and full API fast tests remained green (`19/19`).
- Why it worked: existing integration harness made it straightforward to assert provenance rows directly without new fixtures.
- Promotion decision: `pilot backlog`
- Why: likely reusable for additional admin endpoints but broader admin domain is not complete yet.

## Receipts
- Commands run:
  - `uv run --project api --extra dev ruff check api/app/services/repository.py api/app/api/routes/admin.py api/tests/test_discovery_jobs_integration.py`
  - `uv run --project api --extra dev mypy api/app`
  - `make db-up`
  - `make db-reset`
  - `UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "admin_source_trust_policy or trust_policy_write_rejects_unknown_merge_routing_key or trust_policy_write_rejects_invalid_merge_action or trust_policy_write_rejects_invalid_route_label"`
  - `uv run --project api --extra dev pytest api/tests --ignore=api/tests/test_discovery_jobs_integration.py`
  - `make db-down`
  - `bash scripts/agent-hygiene-check.sh --mode project`
- Files changed:
  - `api/app/services/repository.py`
  - `api/app/api/routes/admin.py`
  - `api/tests/test_discovery_jobs_integration.py`
  - `docs/roadmap/IMPLEMENTATION_PLAN_v1.2.md`
  - `.agent/CONTINUITY.md`
  - `.agent/execplans/active/EP-2026-02-08__bootstrap-foundation-v1.md`
  - `.agent/notes/2026-02-10_f2-policy-audit-events.md`
- Tests/checks:
  - Ruff passed on touched API files.
  - Mypy passed for `api/app`.
  - Targeted DB-backed selector passed (`7/7`).
  - API non-integration tests passed (`19/19`).
  - Agent hygiene check passed (`project` mode).
