# Task
- Request: Continue `H2` beyond trust-policy by shipping moderator/admin cockpit flows and add validation coverage.
- Scope: Backend admin module/job APIs + Next.js operator cockpit UI + server proxy routes + integration contract tests.
- Constraints: Preserve existing API contracts, keep mutations safe/bounded, validate with project commands.

## Actions Taken
1. Added admin API surfaces for operator flows: `GET/PATCH /admin/modules`, `GET /admin/jobs`, `POST /admin/jobs/reap-expired`, `POST /admin/jobs/enqueue-freshness`.
2. Added `/admin/cockpit` UI with candidate queue actions (`patch/merge/override`) and modules/jobs operator panels using Next.js server proxies.
3. Added DB-backed integration tests for new admin module/job contracts and mutation receipts.
4. Added web-side API-contract tests (`node:test`) for cockpit query/proxy path contracts and wired `pnpm --dir web test:contracts`.
5. Updated roadmap/continuity/runbook/execplan notes to reflect new `H2` baseline and remaining `L1` E2E gap.
6. Executed live Chrome DevTools cockpit smoke validation against local API/web stack and verified successful network payloads for merge/patch/override, module toggles, and jobs maintenance actions.
7. Added Playwright browser automation for the cockpit path (`web/tests-e2e/admin-cockpit.spec.ts`) with mocked `/api/admin/*` contracts and wired `pnpm --dir web test:e2e`.
8. Added live backend-driven cockpit Playwright coverage (`web/tests-e2e/admin-cockpit.live.spec.ts`) with local mock Supabase auth server orchestration (`scripts/mock_supabase_auth.py`) and dedicated config/scripts (`web/playwright.live.config.ts`, `pnpm --dir web test:e2e:live`).
9. Wired CI live browser coverage job (`web-e2e-live`) with Postgres service + schema apply + `uv` setup in `.github/workflows/ci.yml`.

## What Went Wrong
1. Issue: First DB-backed test run failed in sandbox with local Postgres connection denial.
- Root cause: Sandbox blocks localhost socket access for asyncpg.
- Early signal missed: This repo already had a helper/receipt pattern for escalated DB-backed tests.
- Prevention rule: Run DB-backed pytest with escalation immediately when asyncpg localhost access is required.
2. Issue: Initial attempts to create Next.js dynamic-route folders failed.
- Root cause: zsh interpreted `[candidateId]` as glob patterns.
- Early signal missed: Command used unquoted paths with brackets.
- Prevention rule: Always quote bracketed app-router paths (`'[param]'`) in shell commands.
3. Issue: Chrome DevTools MCP transport became unavailable (`Transport closed`) during follow-up validation attempts.
- Root cause: Local DevTools helper process state drifted from MCP tool lifecycle in the session.
- Early signal missed: repeated `list_pages` failures indicated bridge-level outage rather than page-level issues.
- Prevention rule: Fall back to Playwright/browser automation when DevTools transport stays closed after one cleanup/reconnect cycle.
4. Issue: Playwright run failed in sandbox because web server bind was denied (`listen EPERM 127.0.0.1:3001`).
- Root cause: sandbox network restrictions block local port binding for this command path.
- Early signal missed: this repo already had a DB-integration escalation helper pattern for localhost constraints.
- Prevention rule: rerun browser E2E commands with escalation immediately after first localhost bind denial.
5. Issue: Live backend E2E initially failed with API validation errors (`422`) on candidate list requests.
- Root cause: test queried `/candidates` with `limit=200`, exceeding API contract max (`<=100`).
- Early signal missed: route schema constraints were already explicit in FastAPI query params.
- Prevention rule: mirror API query bounds in test constants (or add shared helper constants) for any live contract assertions.
6. Issue: Live merge step initially failed with `cannot merge candidates that both already have postings`.
- Root cause: seed flow created postings for both primary and secondary candidates.
- Early signal missed: merge semantics require at most one side to have a posting record.
- Prevention rule: seed secondary candidate with extract output that omits posting projection when testing merge path.
7. Issue: Live Playwright API server bootstrap failed on local Python (`No module named uvicorn`).
- Root cause: `playwright.live.config.ts` launched `python -m uvicorn` outside managed project deps.
- Early signal missed: repo standard is `uv run --project api --extra dev ...` for reproducible API commands.
- Prevention rule: use `uv run` for API process startup in all scripted/local/CI test harnesses.

## What Went Right
1. Improvement: Shared admin proxy helper reduced repeated env/error handling across all new web proxy routes.
- Evidence (time/readability/performance/manageability/modularity): One place for bearer/env parsing; new routes are thin passthrough files.
- Why it worked: Existing trust-policy proxy pattern was already stable and easy to generalize.
2. Improvement: Contract-first backend tests caught authz/mutation behavior at API boundaries for modules/jobs.
- Evidence (time/readability/performance/manageability/modularity): `4/4` targeted DB integration tests validate read and safe-mutation paths.
- Why it worked: Reused established integration test fixture/auth mocking patterns.
3. Improvement: Browser-side network traces made manual E2E validation concrete even without full Playwright coverage.
- Evidence (time/readability/performance/manageability/modularity): Captured `200` responses and returned bodies for candidate actions (`reqid=17/19/25`), module toggles (`reqid=28/30`), and job maintenance (`reqid=32/34`).
- Why it worked: DevTools request inspection exposed exact request/response contracts beyond UI toast text.
4. Improvement: Mock-backed Playwright cockpit flow now provides deterministic browser-level regression coverage without requiring API/DB orchestration.
- Evidence (time/readability/performance/manageability/modularity): `pnpm --dir web test:e2e` passes (`1/1`) validating merge/patch/override/module-toggle/jobs-maintenance UI flows and request payload contracts.
- Why it worked: Route interception isolates UI contract behavior and keeps runtime dependencies minimal.
5. Improvement: Live backend-driven cockpit browser test now verifies persisted outcomes (candidate state, merged discovery IDs, posting status, module final enabled state) against real API/DB.
- Evidence (time/readability/performance/manageability/modularity): `pnpm --dir web test:e2e:live` passes (`1/1`) after deterministic seeding + assertions.
- Why it worked: layered harness (mock Supabase + uv-run API + Next dev server) preserved real backend behavior while keeping auth deterministic.
6. Improvement: CI now includes dedicated `web-e2e-live` job, closing the previous gap where browser moderation coverage existed only locally.
- Evidence (time/readability/performance/manageability/modularity): new workflow job provisions Postgres, applies schema, and executes live Playwright suite.
- Why it worked: existing DB integration workflow patterns were reusable for browser E2E setup.

## Reusable Learnings
1. Learning: Admin operator surfaces should expose only bounded actions first (`enabled` toggles, queue maintenance triggers) before broader mutations.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `RUNBOOK.md`
- Why: This keeps blast radius low while still unblocking operational workflows.
2. Learning: Web `typecheck` in this repo can require `.next/types` generation in a clean workspace.
- Promotion decision: `pilot backlog`
- Promote to (if `promote now`): `UNCONFIRMED`
- Why: Current behavior is environment-sensitive; keep as a tracked caution before changing project scripts.
3. Learning: Live UI E2E can remain deterministic by mocking only identity provider surface while keeping app API/database real.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `RUNBOOK.md`
- Why: reduces flakiness and setup burden while preserving confidence in persistence and API contracts.

## Receipts
- Commands run:
  - `uv run --project api --extra dev ruff check api/app/api/routes/admin.py api/app/schemas/admin.py api/app/services/repository.py api/tests/test_discovery_jobs_integration.py`
  - `uv run --project api --extra dev mypy api/app`
  - `make db-up && make db-reset && (escalated) uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "admin_modules_list_and_toggle_enabled or admin_modules_requires_admin_scope or admin_jobs_visibility_and_safe_mutations or admin_jobs_requires_admin_scope" && make db-down`
  - `pnpm --dir web lint && pnpm --dir web build && pnpm --dir web typecheck`
  - `pnpm --dir web test:contracts`
  - `bash scripts/agent-hygiene-check.sh --mode project`
  - Chrome DevTools interactive run at `http://127.0.0.1:3000/admin/cockpit` with network payload inspection (`reqid=17/19/25/28/30/32/34`)
  - `(escalated) fnm exec --using 24.13.0 pnpm --dir web add -D @playwright/test@1.55.0 --store-dir <pnpm-store-dir>`
  - `(escalated) fnm exec --using 24.13.0 pnpm --dir web test:e2e`
  - `(escalated) make db-up && make db-reset`
  - `(escalated) fnm exec --using 24.13.0 pnpm --dir web test:e2e:live`
- Files changed:
  - `api/app/api/routes/admin.py`, `api/app/schemas/admin.py`, `api/app/services/repository.py`
  - `api/tests/test_discovery_jobs_integration.py`
  - `web/app/admin/cockpit/*`, `web/app/api/admin/candidates/**`, `web/app/api/admin/modules/**`, `web/app/api/admin/jobs/**`
  - `web/lib/admin-api.ts`, `web/lib/admin-cockpit.ts`, `web/lib/admin-cockpit-utils.ts`, `web/lib/admin-proxy-paths.ts`, `web/lib/admin-source-trust-policy-api.ts`
  - `web/tests/admin-cockpit-utils.test.ts`, `web/tests/admin-proxy-paths.test.ts`, `web/package.json`, `web/tsconfig.json`
  - `web/playwright.config.ts`, `web/tests-e2e/admin-cockpit.spec.ts`, `.gitignore`, `web/pnpm-lock.yaml`
  - `web/playwright.live.config.ts`, `web/tests-e2e/admin-cockpit.live.spec.ts`, `scripts/mock_supabase_auth.py`, `.github/workflows/ci.yml`
  - `.agent/CONTINUITY.md`, `.agent/RUNBOOK.md`, `.agent/execplans/active/EP-2026-02-08__bootstrap-foundation-v1.md`, `docs/roadmap/IMPLEMENTATION_PLAN_v1.2.md`
- Tests/checks:
  - Targeted DB integration: pass (`4 passed`)
  - API lint/typecheck: pass
  - Web lint/build/typecheck: pass
  - Web contract tests: pass (`9/9`)
  - Manual cockpit browser smoke (Chrome DevTools): pass
  - Web Playwright cockpit E2E (mock): pass (`2/2`)
  - Web Playwright cockpit E2E (live backend): pass (`1/1`)
  - Agent hygiene check: pass
