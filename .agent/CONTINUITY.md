# Continuity Ledger

Facts only. No transcripts. If unknown, write `UNCONFIRMED`.
Each entry must include date and provenance tag: `[USER]`, `[CODE]`, `[TOOL]`, `[ASSUMPTION]`.
In `project` mode, update this file whenever Goal/Now/Next/Decisions materially change.
In `template` mode, keep this file as scaffold-only.

## Size caps
- Snapshot: <= 25 non-empty lines.
- Done (recent): <= 7 bullets.
- Working set: <= 12 bullets.
- Receipts: <= 20 bullets (keep recent, compress older items).

## Snapshot

Goal: Ship Phase 1 baseline with DB-backed API persistence/auth, worker compatibility, and CI quality gates.
Now: `H2` operator cockpit baseline is live with Next.js `/admin/cockpit` candidate queue actions (`PATCH /candidates`, `POST /candidates/{id}/merge`, `POST /candidates/{id}/override`) and admin module/job flows (`GET/PATCH /admin/modules`, `GET /admin/jobs`, `POST /admin/jobs/reap-expired`, `POST /admin/jobs/enqueue-freshness`) through server proxy routes, with automated Playwright cockpit browser coverage added for merge/patch/override + module/job operator actions.
Next: Expand `L1` browser coverage from mock-backed cockpit flows to live backend-backed E2E assertions (including explicit posting-status readback after override).
Open Questions: exact production Supabase URL/key provisioning and human role metadata conventions are UNCONFIRMED.

## Done (recent)
- 2026-02-10 `[CODE]` Added admin policy-management endpoints (`GET/PUT/PATCH /admin/source-trust-policy`) plus provenance audit writes (`policy_upserted`, `policy_enabled_changed`) with actor attribution and prior/new enabled state payloads.
- 2026-02-10 `[CODE]` Expanded integration API coverage to assert admin trust-policy CRUD/filter/authz, audit receipts, and invalid-rules contract failures.
- 2026-02-10 `[CODE]` Added `RUNBOOK` API-first trust-policy operator snippets and Next.js trust-policy UI/proxy routes (`/admin/source-trust-policy`, `/api/admin/source-trust-policy`).
- 2026-02-10 `[CODE]` Added admin operator cockpit baseline: new admin API module/job endpoints with provenance-backed safe mutations, Next.js `/admin/cockpit` candidate action workflows, and server proxy routes for candidates/modules/jobs operations.
- 2026-02-10 `[CODE]` Added web-side API-contract tests (`node:test`) for cockpit query encoding and admin proxy route path builders; wired `pnpm --dir web test:contracts`.
- 2026-02-10 `[TOOL]` Completed manual Chrome DevTools cockpit smoke flow (`merge -> patch -> override -> module disable/enable -> enqueue/reap`) with successful 200 responses and expected returned payloads.
- 2026-02-10 `[CODE]` Added Playwright browser automation (`web/tests-e2e/admin-cockpit.spec.ts`) and config/scripts (`web/playwright.config.ts`, `pnpm --dir web test:e2e`) for mock-backed cockpit merge/patch/override + module/job operator flows.

## Working set
- 2026-02-08 `[ASSUMPTION]` Target stack remains Next.js + FastAPI + Supabase + Cloud Run per spec.
- 2026-02-08 `[CODE]` Node toolchain standardized on `fnm` + `pnpm` with root `.node-version` and `web/pnpm-lock.yaml`.
- 2026-02-08 `[CODE]` Local API `make test` keeps integration tests skipped unless DB URL env vars are set (while `make test-integration` enforces DB-backed run).

## Decisions
- 2026-02-08 `[CODE]` D-001 through D-004 active in `.agent/DECISIONS.md`.

## Receipts
- 2026-02-10 `[TOOL]` `python -m compileall api/app workers/app` passed.
- 2026-02-10 `[TOOL]` `uv run --project api --extra dev ruff check api/app/api/router.py api/app/api/routes/admin.py api/app/schemas/admin.py api/app/services/repository.py api/tests/test_discovery_jobs_integration.py` passed.
- 2026-02-10 `[TOOL]` `uv run --project api --extra dev mypy api/app` passed.
- 2026-02-10 `[TOOL]` `make db-up -> make db-reset -> (escalated) UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "admin_modules_list_and_toggle_enabled or admin_modules_requires_admin_scope or admin_jobs_visibility_and_safe_mutations or admin_jobs_requires_admin_scope" -> make db-down` passed (`4/4` selected).
- 2026-02-10 `[TOOL]` `uv run --project api --extra dev pytest api/tests --ignore=api/tests/test_discovery_jobs_integration.py` passed (`19/19`).
- 2026-02-10 `[TOOL]` `bash scripts/agent-hygiene-check.sh --mode project` passed.
- 2026-02-10 `[TOOL]` `pnpm --dir web test:contracts` passed (`9/9`).
- 2026-02-10 `[TOOL]` `pnpm --dir web lint` passed.
- 2026-02-10 `[TOOL]` `pnpm --dir web build -> pnpm --dir web typecheck` passed.
- 2026-02-10 `[TOOL]` Chrome DevTools network validation on `http://127.0.0.1:3000/admin/cockpit` confirmed successful candidate merge/patch/override (`reqid=17/19/25`), module toggle disable/enable (`reqid=28/30`), and jobs maintenance counts (`reqid=32 -> {"count":0}`, `reqid=34 -> {"count":0}`).
- 2026-02-10 `[TOOL]` `(escalated) fnm exec --using 24.13.0 pnpm --dir web test:e2e` passed (`1/1`) after local webserver bind was blocked in sandbox (`listen EPERM`).
- 2026-02-10 `[TOOL]` `fnm exec --using 24.13.0 pnpm --dir web test:contracts -> lint -> typecheck` passed after Playwright additions.
