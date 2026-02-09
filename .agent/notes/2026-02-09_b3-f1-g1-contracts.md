# Task Note: 2026-02-09 b3-f1-g1-contracts

## Task
- Request: continue with `B3 + F1 + G1`.
- Scope: deepen moderation/auth baseline and implement public postings detail/filter/sort/search contract coverage.
- Constraints: preserve existing DB-backed flows and validate with integration tests.

## Actions Taken
1. Hardened human role resolution to trust elevated roles only from Supabase `app_metadata` (`role`, `sj_role`, `roles[]`).
2. Implemented moderation transition semantics in candidate state patching, including transition validation and posting lifecycle status coupling.
3. Added public postings detail endpoint and expanded list behavior with search/filter/sort/pagination parameters.
4. Added/expanded tests for moderation authz + transition behavior and postings contract behavior.
5. Re-ran DB-backed integration suite to verify no regressions in discovery/job/projection paths.

## What Went Wrong
1. Issue: immediate `make db-reset` after startup briefly failed because compose service was not yet ready.
- Root cause: startup readiness race.
- Early signal missed: reset was invoked immediately after first startup call.
- Prevention rule: expect compose readiness jitter and retry reset/start sequence when service health has not converged yet.

## What Went Right
1. Improvement: moderation transitions now enforce explicit state progression rules.
- Evidence (manageability): invalid transitions return conflict, and valid transitions update candidate/posting state consistently.
- Why it worked: transition and lifecycle logic is centralized in repository transaction flow.
2. Improvement: public postings API now exposes practical read contracts for prototype UX.
- Evidence (manageability): integration tests now validate list filtering/search/sorting/pagination and detail retrieval.
- Why it worked: list query added bounded, parameterized filtering and deterministic ordering.

## Reusable Learnings
1. Learning: keep moderation state rules server-side and transactional with projection lifecycle updates.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `PATTERNS.md`
- Why: prevents route-level drift and keeps moderation behavior auditable.
2. Learning: add deterministic tie-break ordering (`id`) in sorted list queries to stabilize pagination contracts.
- Promotion decision: `pilot backlog`
- Promote to (if `promote now`): `PATTERNS.md`
- Why: useful broadly, but should be validated against full-text relevance ordering decisions first.

## Receipts
- Commands run:
- `python3 -m compileall api/app api/tests`
- `uv run --project api --extra dev ruff check api/app api/tests`
- `uv run --project api --extra dev mypy api/app`
- `uv run --project api --extra dev pytest api/tests/test_candidates_authz.py api/tests/test_health.py`
- `make db-up`
- `make db-reset`
- `SJ_DATABASE_URL=... SJ_JOB_RETRY_BASE_SECONDS=0 uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py`
- `make db-down`
- Files changed:
- `api/app/core/security.py`
- `api/app/api/routes/candidates.py`
- `api/app/api/routes/postings.py`
- `api/app/api/router.py`
- `api/app/schemas/candidates.py`
- `api/app/schemas/postings.py`
- `api/app/services/repository.py`
- `api/tests/test_candidates_authz.py`
- `api/tests/test_discovery_jobs_integration.py`
- `.agent` continuity/plan/notes updates
- Tests/checks:
- authz + health tests passed (`7/7`).
- DB-backed integration tests passed (`9/9`).
