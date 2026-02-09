# Task Note: 2026-02-09 b3-f1-moderation-authz

## Task
- Request: proceed with next implementation step (`B3 + F1`) and clarify role/ownership model.
- Scope: enforce trusted Supabase role-claim contract, add baseline moderation endpoints, and cover role allow/deny behavior in tests.
- Constraints: keep auth boundaries explicit (human vs machine) and preserve existing integration behavior.

## Actions Taken
1. Hardened role resolution to trusted Supabase `app_metadata` claims only (`role`, `sj_role`, `roles[]`), defaulting to `user`.
2. Added moderation API endpoints: `GET /candidates` and `PATCH /candidates/{id}` with `moderation:read/write` scope checks.
3. Added repository methods for candidate listing and state patching, including provenance events for moderation state changes.
4. Added authz tests for moderation routes and role-claim resolution behavior.
5. Re-ran DB-backed integration regression suite to confirm no regressions in discovery/job/projection flows.

## What Went Wrong
1. Issue: DB reset initially failed (`service "postgres" is not running`) right after container startup.
- Root cause: compose startup race during immediate reset.
- Early signal missed: reset executed before container was fully available.
- Prevention rule: for compose-backed integration runs, tolerate startup races by retrying `db-up/reset` sequence (or add explicit health wait).

## What Went Right
1. Improvement: elevated moderation privileges now depend on trusted role claims only.
- Evidence (manageability/security): user-editable metadata is no longer used for elevated roles.
- Why it worked: role resolution is constrained to `app_metadata` and normalized to allowed roles.
2. Improvement: moderation baseline is now testable end-to-end at API contract level.
- Evidence (manageability): new authz tests cover role allow/deny for `/candidates` operations.
- Why it worked: dependency overrides and mocked Supabase user fetch isolate auth behavior without DB coupling.

## Reusable Learnings
1. Learning: treat role claims as privileged config, not user profile data; only trust claim sources controlled by operators.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `PATTERNS.md`
- Why: directly reduces privilege-escalation risk in any Supabase-backed auth integration.
2. Learning: keep moderation endpoints thin by delegating mutation/provenance to repository methods.
- Promotion decision: `pilot backlog`
- Promote to (if `promote now`): `PATTERNS.md`
- Why: already useful here, but should be validated across additional moderation actions beyond state patching.

## Receipts
- Commands run:
- `python3 -m compileall api/app api/tests`
- `uv run --project api --extra dev ruff check ...`
- `uv run --project api --extra dev mypy api/app`
- `uv run --project api --extra dev pytest api/tests/test_candidates_authz.py api/tests/test_health.py`
- `make db-up`
- `make db-reset`
- `SJ_DATABASE_URL=... SJ_JOB_RETRY_BASE_SECONDS=0 uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py`
- `make db-down`
- Files changed:
- `api/app/core/security.py`
- `api/app/schemas/candidates.py`
- `api/app/api/routes/candidates.py`
- `api/app/api/router.py`
- `api/app/services/repository.py`
- `api/tests/test_candidates_authz.py`
- capture files in `.agent/`
- Tests/checks:
- authz + health tests passed (`7/7`).
- DB-backed discovery/jobs/projection integration tests passed (`5/5`).
