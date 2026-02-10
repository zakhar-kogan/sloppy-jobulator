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
Now: `H2` trust-policy admin UI is wired to `GET/PUT/PATCH /admin/source-trust-policy` through Next.js server proxy routes and supports list/upsert/enable-toggle flows.
Next: Continue `H2` operator cockpit coverage beyond trust-policy management (moderation queues/merge tooling/modules/jobs) while preserving existing API contracts.
Open Questions: exact production Supabase URL/key provisioning and human role metadata conventions are UNCONFIRMED.

## Done (recent)
- 2026-02-10 `[CODE]` Added strict repository validation for `source_trust_policy.rules_json` merge-routing contracts (top-level key whitelist, decision-map unknown-key rejection, action whitelist, route-label format checks).
- 2026-02-10 `[CODE]` Added admin policy-management endpoints (`GET/PUT/PATCH /admin/source-trust-policy`) with `admin:write` scope enforcement and repository-backed list/upsert/enable-toggle behavior.
- 2026-02-10 `[CODE]` Added provenance audit writes for admin trust-policy operations (`policy_upserted`, `policy_enabled_changed`) with actor attribution and prior/new enabled state payloads.
- 2026-02-10 `[CODE]` Expanded integration API coverage to assert admin trust-policy audit events plus CRUD/filter/authz and invalid-rules contract failures.
- 2026-02-10 `[CODE]` Added `RUNBOOK` API-first trust-policy operator snippets (`curl` list/upsert/toggle), validation expectations, and SQL audit verification queries; updated roadmap follow-up to focus on `H2` wiring.
- 2026-02-10 `[CODE]` Added Next.js admin trust-policy console (`/admin/source-trust-policy`) plus server-side proxy routes (`/api/admin/source-trust-policy`) to execute list/upsert/enable-toggle flows against the API surface with env-based admin bearer auth.

## Working set
- 2026-02-08 `[ASSUMPTION]` Target stack remains Next.js + FastAPI + Supabase + Cloud Run per spec.
- 2026-02-08 `[CODE]` Node toolchain standardized on `fnm` + `pnpm` with root `.node-version` and `web/pnpm-lock.yaml`.
- 2026-02-08 `[CODE]` Local API `make test` keeps integration tests skipped unless DB URL env vars are set (while `make test-integration` enforces DB-backed run).

## Decisions
- 2026-02-08 `[CODE]` D-001 through D-004 active in `.agent/DECISIONS.md`.

## Receipts
- 2026-02-10 `[TOOL]` `uv run --project api --extra dev ruff check api/app/api/router.py api/app/api/routes/admin.py api/app/schemas/admin.py api/app/services/repository.py api/tests/test_discovery_jobs_integration.py` passed.
- 2026-02-10 `[TOOL]` `uv run --project api --extra dev mypy api/app` passed.
- 2026-02-10 `[TOOL]` `make db-up -> make db-reset -> (escalated) UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "admin_source_trust_policy or trust_policy_write_rejects_unknown_merge_routing_key or trust_policy_write_rejects_invalid_merge_action or trust_policy_write_rejects_invalid_route_label" -> make db-down` passed (`7/7` selected).
- 2026-02-10 `[TOOL]` `uv run --project api --extra dev pytest api/tests --ignore=api/tests/test_discovery_jobs_integration.py` passed (`19/19`).
- 2026-02-10 `[TOOL]` `bash scripts/agent-hygiene-check.sh --mode project` passed.
- 2026-02-10 `[TOOL]` `pnpm --dir web lint` passed.
- 2026-02-10 `[TOOL]` `pnpm --dir web typecheck` passed.
- 2026-02-10 `[TOOL]` `pnpm --dir web build` passed.
