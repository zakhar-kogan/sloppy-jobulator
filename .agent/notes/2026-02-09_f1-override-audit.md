# Task Note: 2026-02-09 f1-override-audit

## Task
- Request: proceed with next `B3 + F1 + G1` implementation steps.
- Scope: close remaining moderation baseline gap by adding explicit override semantics and validating full moderation audit path.

## Actions Taken
1. Added `POST /candidates/{candidate_id}/override` moderation endpoint with `moderation:write` guard.
2. Added override payload schema supporting target `state`, optional `reason`, and optional posting status override.
3. Implemented transactional repository override behavior with:
- candidate state update bypassing normal transition guard rails,
- optional posting status override coupling,
- provenance events (`state_overridden`) for both candidate and posting entities.
4. Expanded authz tests for override deny/allow behavior.
5. Added DB-backed integration test proving:
- normal invalid transition remains blocked via `PATCH /candidates/{id}`,
- override succeeds for the same target state,
- posting override is applied,
- audit events are queryable from `/candidates/{id}/events`.
6. Updated roadmap/continuity capture to reflect F1 completion and E4 partial progress.
7. Added runbook section for Supabase role provisioning conventions used by API role resolution.

## What Went Wrong
1. No implementation defect surfaced; main risk was ambiguity around override semantics.
- Root cause: spec-level term `override` is broad.
- Prevention rule: keep override scope explicit in API contract and prove behavior with integration tests before extending semantics.

## What Went Right
1. Improvement: moderation now supports state patch + merge + override with auditable events.
- Evidence (manageability): integration coverage increased from 11 to 12 DB-backed scenarios and includes override audit checks.
- Why it worked: repository-level transactional updates keep candidate/posting state and provenance writes consistent.

## Reusable Learnings
1. Learning: treat moderation overrides as explicit endpoints instead of overloading normal state transitions.
- Promotion decision: `pilot backlog`
- Why: useful pattern for operator actions, but final domain semantics should be revisited alongside moderation UI/API versioning.
2. Learning: verify override semantics by pairing negative-path (`PATCH` conflict) and positive-path (`/override` success) tests in the same flow.
- Promotion decision: `promote now`
- Promote to: `PATTERNS.md`
- Why: sharply reduces ambiguity around exceptional control paths.

## Receipts
- Commands run:
- `uv run --project api --extra dev ruff check api/app api/tests`
- `uv run --project api --extra dev mypy api/app`
- `uv run --project api --extra dev pytest api/tests/test_candidates_authz.py api/tests/test_health.py`
- `make db-up`
- `make db-reset`
- `SJ_DATABASE_URL=... SJ_JOB_RETRY_BASE_SECONDS=0 uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py`
- `make db-down`
- Files changed:
- `api/app/schemas/candidates.py`
- `api/app/api/routes/candidates.py`
- `api/app/services/repository.py`
- `api/tests/test_candidates_authz.py`
- `api/tests/test_discovery_jobs_integration.py`
- `docs/roadmap/IMPLEMENTATION_PLAN_v1.2.md`
- `.agent/RUNBOOK.md`
- `.agent/CONTINUITY.md`
- `.agent/notes/2026-02-09_f1-override-audit.md`
- Validation:
- Lint/type checks passed.
- Fast API tests passed (`11/11`).
- DB-backed integration tests passed (`12/12`).
