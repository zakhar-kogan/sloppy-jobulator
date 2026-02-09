# Task Note: 2026-02-09 d2-lease-retry-deadletter

## Task
- Request: proceed with D2.
- Scope: implement lease reaper + retry/dead-letter transitions and add integration coverage.
- Constraints: preserve existing API contracts where possible and validate via DB-backed tests.

## Actions Taken
1. Added API support for lease reaping (`POST /jobs/reap-expired`) with repository-level expired-claim requeue behavior and provenance events.
2. Extended job result handling so `failed` transitions resolve to `queued` with backoff or `dead_letter` at max attempts, with explicit provenance for retry/dead-letter events.
3. Added API settings for retry policy (`SJ_JOB_MAX_ATTEMPTS`, `SJ_JOB_RETRY_BASE_SECONDS`, `SJ_JOB_RETRY_MAX_SECONDS`).
4. Updated worker runtime to trigger lease reaping periodically and submit `failed` results when execution raises.
5. Added integration tests for expired lease requeue and bounded retry/dead-letter flow.

## What Went Wrong
1. Issue: `uv` commands for DB-backed API tests failed under sandbox due to global cache access.
- Root cause: `uv` cache path is outside workspace sandbox.
- Early signal missed: direct rerun attempted before escalating.
- Prevention rule: for `uv run` commands that use global cache, request escalation immediately after sandbox denial and continue with the same command.

## What Went Right
1. Improvement: reliability transitions are now explicit and observable.
- Evidence (manageability): lease requeue, retry scheduling, and dead-letter outcomes emit distinct provenance events.
- Why it worked: all transitions are centralized in repository transaction logic around job state updates.
2. Improvement: D2 behavior is validated by integration tests, not only unit tests.
- Evidence (manageability): integration suite now covers projection path and D2 paths (5 total integration tests).
- Why it worked: tests assert persisted DB state and provenance outcomes directly.

## Reusable Learnings
1. Learning: resolve `failed` processor results server-side into deterministic retry/dead-letter transitions using the persisted `attempt` counter.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `PATTERNS.md`
- Why: keeps failure semantics consistent across all processors and avoids worker-specific retry drift.
2. Learning: periodic lease reaper calls can be piggybacked on worker polling loop as a bootstrap scheduler.
- Promotion decision: `pilot backlog`
- Promote to (if `promote now`): `RUNBOOK.md`
- Why: effective for current scale, but cadence and batch sizing need more production evidence.

## Receipts
- Commands run:
- `python3 -m compileall api/app api/tests workers/app workers/tests`
- `uv run --project api --extra dev ruff check api/app/core/config.py api/app/schemas/jobs.py api/app/api/routes/jobs.py api/app/services/repository.py api/tests/test_discovery_jobs_integration.py`
- `uv run --project api --extra dev mypy api/app/services/repository.py`
- `uv run --project workers --extra dev mypy workers/app`
- `uv run --project workers --extra dev pytest workers/tests`
- `make db-up`
- `make db-reset`
- `SJ_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sloppy_jobulator DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sloppy_jobulator SJ_JOB_RETRY_BASE_SECONDS=0 uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py`
- `make db-down`
- Files changed:
- `api/app/core/config.py`
- `api/app/schemas/jobs.py`
- `api/app/api/routes/jobs.py`
- `api/app/services/repository.py`
- `api/tests/test_discovery_jobs_integration.py`
- `workers/app/core/config.py`
- `workers/app/services/job_client.py`
- `workers/app/main.py`
- `.agent` capture/plan files
- Tests/checks:
- API lint/typecheck on touched files passed.
- Worker mypy + tests passed.
- DB-backed integration tests passed (`5/5`).
