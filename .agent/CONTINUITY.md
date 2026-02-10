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
Now: `H2` operator cockpit baseline is live with Next.js `/admin/cockpit` candidate queue actions (`PATCH /candidates`, `POST /candidates/{id}/merge`, `POST /candidates/{id}/override`) and admin module/job flows (`GET/PATCH /admin/modules`, `GET /admin/jobs`, `POST /admin/jobs/reap-expired`, `POST /admin/jobs/enqueue-freshness`) through server proxy routes.
Next: Harden `H2/L1` with dedicated web-side contract/component tests and later full E2E moderation/admin flows.
Open Questions: exact production Supabase URL/key provisioning and human role metadata conventions are UNCONFIRMED.

## Done (recent)
- 2026-02-10 `[CODE]` Added strict repository validation for `source_trust_policy.rules_json` merge-routing contracts (top-level key whitelist, decision-map unknown-key rejection, action whitelist, route-label format checks).
- 2026-02-10 `[CODE]` Added admin policy-management endpoints (`GET/PUT/PATCH /admin/source-trust-policy`) with `admin:write` scope enforcement and repository-backed list/upsert/enable-toggle behavior.
- 2026-02-10 `[CODE]` Added provenance audit writes for admin trust-policy operations (`policy_upserted`, `policy_enabled_changed`) with actor attribution and prior/new enabled state payloads.
- 2026-02-10 `[CODE]` Expanded integration API coverage to assert admin trust-policy audit events plus CRUD/filter/authz and invalid-rules contract failures.
- 2026-02-10 `[CODE]` Added `RUNBOOK` API-first trust-policy operator snippets (`curl` list/upsert/toggle), validation expectations, and SQL audit verification queries; updated roadmap follow-up to focus on `H2` wiring.
- 2026-02-10 `[CODE]` Added Next.js admin trust-policy console (`/admin/source-trust-policy`) plus server-side proxy routes (`/api/admin/source-trust-policy`) to execute list/upsert/enable-toggle flows against the API surface with env-based admin bearer auth.
- 2026-02-10 `[CODE]` Added admin operator cockpit baseline: new admin API module/job endpoints with provenance-backed safe mutations, Next.js `/admin/cockpit` candidate action workflows, and server proxy routes for candidates/modules/jobs operations.

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
- 2026-02-10 `[TOOL]` `pnpm --dir web lint` passed.
- 2026-02-10 `[TOOL]` `pnpm --dir web build -> pnpm --dir web typecheck` passed.
