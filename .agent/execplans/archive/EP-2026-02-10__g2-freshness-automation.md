# Plan ID: EP-2026-02-10__g2-freshness-automation

## Metadata
- Status: `ARCHIVED`
- Created: `2026-02-10`
- Last Updated: `2026-02-10`
- Owner: `Codex`
- Archived: `2026-02-10`

## Purpose / Big Picture
Implement `G2` freshness automation so postings are rechecked on a daily cadence and automatically downgraded/archived after bounded retries, with deterministic provenance.

## Scope and Constraints
- In scope:
1. Add freshness job scheduling endpoint/logic.
2. Add worker automation to enqueue and execute `check_freshness`.
3. Apply posting lifecycle transitions from freshness results and dead-letter exhaustion.
4. Add integration/unit coverage for enqueue and transition paths.
- Out of scope:
1. External URL live-check implementation.
2. OTel/structured logging enrichment.
3. Dedupe scorer (`E3`) and merge policy engine completion (`E4`).
- Constraints:
1. Keep existing job API (`GET/claim/result`) contract stable.
2. Preserve centralized retry/dead-letter machinery.
3. Keep transition updates auditable and transactional.

## Progress
- [x] Add `POST /jobs/enqueue-freshness` endpoint and repository scheduler.
- [x] Add repository freshness result/dead-letter transition application.
- [x] Add worker freshness enqueue cadence + `check_freshness` evaluator.
- [x] Add DB-backed integration tests and worker unit tests.
- [x] Run lint/typecheck/tests for changed paths.

## Decision Log
- 2026-02-10: Reused existing job retry/dead-letter logic for freshness instead of introducing a parallel scheduler state machine.
- 2026-02-10: Applied posting/candidate transitions in the same transaction as job result submission to keep audit consistency.
- 2026-02-10: Added explicit no-op behavior when freshness-recommended transitions are no longer valid at execution time.

## Plan of Work
1. API scheduler:
- Paths: `api/app/api/routes/jobs.py`, `api/app/schemas/jobs.py`, `api/app/services/repository.py`, `api/app/core/config.py`.
2. Worker orchestration:
- Paths: `workers/app/main.py`, `workers/app/services/job_client.py`, `workers/app/jobs/executor.py`, `workers/app/jobs/freshness.py`, `workers/app/core/config.py`.
3. Validation:
- Paths: `api/tests/test_discovery_jobs_integration.py`, `workers/tests/test_freshness.py`.

## Validation and Acceptance
1. `UV_CACHE_DIR=/tmp/uv-cache uv run --project workers --extra dev pytest workers/tests -q`
- Expected: worker test suite passes including freshness evaluator cases.
2. `UV_CACHE_DIR=/tmp/uv-cache uv run --project api --extra dev ruff check ...` and `UV_CACHE_DIR=/tmp/uv-cache uv run --project workers --extra dev ruff check ...`
- Expected: lint passes for touched files.
3. `UV_CACHE_DIR=/tmp/uv-cache uv run --project api --extra dev mypy api/app` and `UV_CACHE_DIR=/tmp/uv-cache uv run --project workers --extra dev mypy workers/app`
- Expected: typechecks pass for changed modules.
4. `make db-up -> make db-reset -> SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "enqueue_freshness_jobs or freshness_dead_letter" -> make db-down`
- Expected: 2/2 targeted freshness integration tests pass.

## Idempotence and Recovery
1. Freshness scheduler suppresses duplicate pending jobs for the same posting.
2. Failed freshness results reuse existing bounded retries before dead-letter downgrade/archive fallback.
3. If freshness behavior regresses, changes are isolated to job route/repository and worker freshness handler paths for targeted rollback.

## Outcomes and Retrospective
- Outcome: `ARCHIVED`
- What shipped:
1. Daily freshness enqueue endpoint + worker automation.
2. Freshness job result handling with deterministic posting transitions.
3. Retry-exhausted fallback transitions and provenance event coverage.
4. Worker/API tests for freshness scheduling and transition behavior.
- Follow-ups:
1. Implement `E3` dedupe scorer and integrate with `E4` merge policy routing.
