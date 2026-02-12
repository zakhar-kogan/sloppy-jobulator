# Task Note: J1/J2/M1 env bindings + E2 redirect semantics + H2/L1 E2E breadth

## Task
- Request: Continue backlog items for `J1/J2/M1`, `H2/L1`, and `E2`.
- Scope: Add deploy/binding assets, incremental redirect-resolution path, and expanded cockpit E2E scenarios.
- Constraints: Keep contracts stable, preserve async redirect behavior, validate with targeted checks.

## Actions Taken
1. Added project-mode execplan `EP-2026-02-12__env-bindings-e2-h2l1` and indexed it.
2. Added `docs/ENVIRONMENT_BINDINGS.md`, staged deploy workflow (`.github/workflows/deploy.yml`), and observability bind/import/telemetry validation scripts.
3. Added environment-bindable observability templates (`docs/observability/*.template.*`) and updated observability/runbook docs.
4. Implemented incremental E2 redirect resolution:
- Worker resolver (`workers/app/jobs/redirects.py`) with redirect-chain semantics and normalization overrides.
- Executor routing for `resolve_url_redirects`.
- API normalization override support (`api/app/core/urls.py`, config + discovery route wiring).
- Repository handling for metadata-gated redirect-job enqueue and persisted discovery URL/hash updates with provenance.
5. Expanded `H2/L1` Playwright cockpit coverage with queue/filter/pagination cross-flow scenarios in both mock and live specs.

## What Went Wrong
1. Issue: New API package metadata folder (`api/sloppy_jobulator_api.egg-info`) appeared after editable install checks.
- Root cause: `uv` editable build artifact creation during local test runs.
- Early signal missed: no explicit post-check cleanup in command plan.
- Prevention rule: remove generated editable-build artifacts before final diff review.
2. Issue: New live pagination E2E initially failed.
- Root cause: test assumed UUID text parse from a single row and later queried `/candidates` with `limit=200` exceeding API cap (`<=100`).
- Early signal missed: helper limits in existing API contracts were not reused in the new poll assertion.
- Prevention rule: reuse API-constrained helper queries and avoid parsing row text when candidate IDs can be sourced from API fixtures.

## What Went Right
1. Improvement: Redirect-resolution rollout was incremental and low-risk.
- Evidence (time/readability/performance/manageability/modularity): metadata-gated enqueue avoided breaking existing ingest flow/tests while allowing E2 behavior and coverage to land.
- Why it worked: isolate new behavior behind explicit signal until full E1/E2 contract is finalized.
2. Improvement: Staging/prod observability/deploy binding is now executable and documented.
- Evidence (time/readability/performance/manageability/modularity): one bindings doc + workflow + scripts now encode required secrets and run order.
- Why it worked: centralized environment contract reduced ambiguity across J1/J2/M1 tasks.

## Reusable Learnings
1. Learning: Incremental rollout for new async job kinds should be metadata/flag gated until downstream queue contracts are updated.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `RUNBOOK.md`
- Why: prevents broad integration test churn and keeps behavior reversible.
2. Learning: Environment-bound observability import should be template-rendered from tracked artifacts, not manual edits per env.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `RUNBOOK.md`
- Why: deterministic render/import path reduces operator mistakes during staged deploys.
3. Learning: Full DB integration checks remain blocked in sessions without DB env wiring; keep targeted fast checks plus explicit gap note.
- Promotion decision: `pilot backlog`
- Promote to (if `promote now`): `helpers/`
- Why: useful if repeated across sessions, but needs another failure cycle to justify helper creation.

## Receipts
- Commands run:
  - `uv run --project workers --extra dev pytest workers/tests/test_redirects.py workers/tests/test_freshness.py`
  - `uv run --project api --extra dev pytest api/tests/test_urls.py -q`
  - `fnm exec --using 24.13.0 pnpm --dir web exec playwright test web/tests-e2e/admin-cockpit.spec.ts --reporter=line`
  - `uv run --project api --extra dev ruff check ...`
  - `uv run --project workers --extra dev ruff check ...`
  - `uv run --project api --extra dev mypy api/app`
  - `uv run --project workers --extra dev mypy workers/app`
  - `uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k redirect_resolution -q` (skipped: no DB env)
  - `make db-up -> make db-reset -> UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k redirect_resolution -q -> UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... fnm exec --using 24.13.0 pnpm --dir web test:e2e:live -> make db-down` (passed after live test fix)
- Files changed:
  - Deploy/bindings: `.github/workflows/deploy.yml`, `docs/ENVIRONMENT_BINDINGS.md`, `scripts/bind-observability-assets.py`, `scripts/import-observability-assets.sh`, `scripts/validate-telemetry-quality.sh`, `docs/observability/*.template.*`, `docs/observability/README.md`
  - E2/API/workers: `api/app/core/{config,urls}.py`, `api/app/api/routes/discoveries.py`, `api/app/services/repository.py`, `workers/app/core/urls.py`, `workers/app/jobs/{executor,redirects}.py`
  - Tests: `api/tests/test_urls.py`, `api/tests/test_discovery_jobs_integration.py`, `workers/tests/test_redirects.py`, `web/tests-e2e/admin-cockpit{,.live}.spec.ts`
  - Agent capture: `.agent/execplans/*`, `.agent/RUNBOOK.md`, `docs/roadmap/IMPLEMENTATION_PLAN_v1.2.md`
- Tests/checks:
  - Workers pytest: pass
  - API URL unit tests: pass
  - Mock Playwright cockpit spec: pass
  - Ruff + mypy (API/workers): pass
  - DB integration redirect test: skipped (DB env missing)
