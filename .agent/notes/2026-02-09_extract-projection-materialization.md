# Task Note: 2026-02-09 extract-projection-materialization

## Task
- Request: proceed with next implementation steps.
- Scope: complete the next roadmap slice by materializing `extract` job results into candidate/posting records with provenance and integration coverage.
- Constraints: keep contracts stable, keep diffs reviewable, validate with DB-backed integration flow.

## Actions Taken
1. Extended `api/app/services/repository.py` job-result transaction to materialize `posting_candidates`, link `candidate_discoveries`/`candidate_evidence`, project `postings`, and emit candidate/posting provenance events.
2. Added coercion/guard helpers for extract payload fields (state/status/list/datetime/bool parsing) and projection-signal gating to avoid accidental projection from non-posting payloads.
3. Updated `api/tests/test_discovery_jobs_integration.py` to assert discovery -> claim -> done result -> candidate/posting/provenance projection behavior.
4. Updated roadmap/continuity/execplan documents to reflect completed projection baseline and new next priority (`D2`).

## What Went Wrong
1. Issue: `make test-integration` failed in this shell because `pytest` was not installed globally.
- Root cause: make target assumes host-level `pytest`, while this environment uses `uv run --project api`.
- Early signal missed: initial validation attempted with `make test-integration` before confirming toolchain availability in PATH.
- Prevention rule: verify Python tool invocation strategy first; in sandboxed environments prefer `uv run --project api --extra dev pytest ...` for API tests.

## What Went Right
1. Improvement: projection writes are transactional with job completion.
- Evidence (manageability): one DB transaction now persists job terminal state, candidate/posting projection, and provenance for candidate/posting entities.
- Why it worked: projection logic executes inside existing `submit_job_result` transaction, preserving atomicity.
2. Improvement: integration tests now cover the first end-to-end projection path.
- Evidence (manageability): DB-backed integration tests assert candidate state, posting creation, and projection provenance events.
- Why it worked: test payload includes explicit posting fields and validates persisted rows/events directly.

## Reusable Learnings
1. Learning: gate projections on explicit payload signals and required-field completeness before creating public-facing entities.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `PATTERNS.md`
- Why: avoids coupling bootstrap/stub worker outputs to publish-side effects while keeping extraction payloads flexible.
2. Learning: default local validation commands should align with project toolchain (`uv run`) instead of assuming host-installed linters/test runners.
- Promotion decision: `pilot backlog`
- Promote to (if `promote now`): `RUNBOOK.md`
- Why: useful for this repo and likely reusable, but should be validated against existing CI/local contributor setup first.

## Receipts
- Commands run:
- `python3 -m compileall api/app api/tests`
- `python3 -m compileall workers/app workers/tests`
- `uv run --project api --extra dev pytest api/tests/test_health.py`
- `uv run --project api --extra dev ruff check api/app/services/repository.py api/tests/test_discovery_jobs_integration.py`
- `uv run --project api --extra dev mypy api/app/services/repository.py`
- `make db-up`
- `make db-reset`
- `SJ_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sloppy_jobulator DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sloppy_jobulator uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py`
- `make db-down`
- Files changed:
- `api/app/services/repository.py`
- `api/tests/test_discovery_jobs_integration.py`
- `docs/roadmap/IMPLEMENTATION_PLAN_v1.2.md`
- `.agent/CONTINUITY.md`
- `.agent/execplans/active/EP-2026-02-08__bootstrap-foundation-v1.md`
- `.agent/notes/2026-02-09_extract-projection-materialization.md`
- Tests/checks:
- compileall (api/workers) passed.
- API health test passed.
- API lint/typecheck on touched files passed.
- DB-backed API integration suite passed (`3/3`).
