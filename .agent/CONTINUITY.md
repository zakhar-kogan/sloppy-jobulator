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
Now: API integration tests cover discovery->job claim->result flow against Postgres-backed auth/repository paths; CI API job provisions Postgres and applies schema/seed before tests.
Next: Wire environment-specific Supabase URL/key + role metadata conventions for non-local environments and expand integration coverage to posting projection paths.
Open Questions: exact production Supabase URL/key provisioning and human role metadata conventions are UNCONFIRMED.

## Done (recent)
- 2026-02-08 `[CODE]` Replaced in-memory API store with async Postgres repository and DB-backed idempotency/provenance writes for discoveries/evidence/jobs.
- 2026-02-08 `[CODE]` Implemented machine credential validation (`modules` + `module_credentials`) and Supabase-backed human token verification.
- 2026-02-08 `[CODE]` Standardized Node workflows on `fnm` + `pnpm` with root `.node-version` and web lockfile.
- 2026-02-08 `[CODE]` Added CI jobs for api/workers/web lint/typecheck/tests and updated web CI to use `pnpm --frozen-lockfile`.
- 2026-02-08 `[CODE]` Added API integration tests for discovery -> jobs claim/result flow in `api/tests/test_discovery_jobs_integration.py`.
- 2026-02-08 `[CODE]` Updated API CI job with Postgres service + schema/seed apply before tests.
- 2026-02-08 `[CODE]` Moved handoff docs into `docs/spec/` and `docs/roadmap/`, updated references, and removed `handoff/`.

## Working set
- 2026-02-08 `[ASSUMPTION]` Target stack remains Next.js + FastAPI + Supabase + Cloud Run per spec.
- 2026-02-08 `[CODE]` Node toolchain standardized on `fnm` + `pnpm` with root `.node-version` and `web/pnpm-lock.yaml`.
- 2026-02-08 `[CODE]` API integration tests require `SJ_DATABASE_URL|DATABASE_URL`; local runs skip them when DB is not configured.

## Decisions
- 2026-02-08 `[CODE]` D-001 through D-004 active in `.agent/DECISIONS.md`.

## Receipts
- 2026-02-08 `[TOOL]` `python -m compileall api/app workers/app` succeeded after repository/auth rewiring.
- 2026-02-08 `[TOOL]` `uv venv .venv && uv pip install -e './api[dev]' -e './workers[dev]'` installed lint/typecheck/test toolchain locally.
- 2026-02-08 `[TOOL]` `fnm use 24.13.0 && pnpm install --dir web` installed web dependencies and generated `web/pnpm-lock.yaml`.
- 2026-02-08 `[TOOL]` `make lint && make typecheck && make test && make build` all passed locally.
- 2026-02-08 `[TOOL]` Local `make test` ran API integration tests as skipped (no local DB URL configured), while CI now provisions Postgres for those tests.
- 2026-02-08 `[TOOL]` `bash scripts/agent-hygiene-check.sh --mode project` passed after removing absolute-path source references.
