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
Now: API discoveries/evidence/jobs/postings are Postgres-backed; machine credentials validate against `module_credentials`; human auth verifies tokens via Supabase `/auth/v1/user`; handoff docs moved into `docs/`.
Next: Add integration tests for discovery->job->result flow and wire environment-specific Supabase settings in deployment.
Open Questions: exact production Supabase URL/key provisioning and human role metadata conventions are UNCONFIRMED.

## Done (recent)
- 2026-02-08 `[CODE]` Replaced in-memory API store with async Postgres repository (`api/app/services/repository.py`) and removed bootstrap store.
- 2026-02-08 `[CODE]` Wired discovery/evidence/jobs/postings routes to repository methods with DB-backed idempotency and provenance writes.
- 2026-02-08 `[CODE]` Implemented machine credential validation against `modules` + `module_credentials` and human token verification via Supabase Auth API.
- 2026-02-08 `[CODE]` Added dev module/credential seed records and aligned worker default API key to seeded processor key.
- 2026-02-08 `[CODE]` Added `.github/workflows/ci.yml` to run lint/typecheck/tests gates across api/workers/web.
- 2026-02-08 `[CODE]` Moved handoff docs into `docs/spec/` and `docs/roadmap/`, updated references, and removed `handoff/`.

## Working set
- 2026-02-08 `[ASSUMPTION]` Target stack remains Next.js + FastAPI + Supabase + Cloud Run per spec.
- 2026-02-08 `[CODE]` Node toolchain standardized on `fnm` + `pnpm` with root `.node-version` and `web/pnpm-lock.yaml`.
- 2026-02-08 `[CODE]` CI currently runs web lint/typecheck (no web test suite exists yet).

## Decisions
- 2026-02-08 `[CODE]` D-001 and D-002 active in `.agent/DECISIONS.md`.
- 2026-02-08 `[CODE]` D-003 added: handoff documents live under `docs/` instead of transient `handoff/`.

## Receipts
- 2026-02-08 `[TOOL]` `python -m compileall api/app workers/app` succeeded after repository/auth rewiring.
- 2026-02-08 `[TOOL]` `uv venv .venv && uv pip install -e './api[dev]' -e './workers[dev]'` installed lint/typecheck/test toolchain locally.
- 2026-02-08 `[TOOL]` `fnm use 24.13.0 && pnpm install --dir web` installed web dependencies and generated `web/pnpm-lock.yaml`.
- 2026-02-08 `[TOOL]` `make lint && make typecheck && make test && make build` all passed locally.
- 2026-02-08 `[TOOL]` `bash scripts/agent-hygiene-check.sh --mode project` passed after removing absolute-path source references.
