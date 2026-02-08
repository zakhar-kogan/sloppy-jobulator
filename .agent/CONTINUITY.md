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

Goal: Bootstrap project foundation from handoff spec with runnable API/web/worker skeletons and baseline DB schema.
Now: Phase 1 foundation scaffold implemented with local handoff copy, schema migration baseline, and starter endpoints.
Next: Integrate API/worker with Postgres + Supabase auth and replace in-memory stores.
Open Questions: exact Supabase project setup and initial module credential bootstrap flow are UNCONFIRMED.

## Done (recent)
- 2026-02-08 `[USER]` Requested implementation start from `/handoff` and approved using `project` mode.
- 2026-02-08 `[TOOL]` Copied handoff docs into local `handoff/` from sibling repo bundle.
- 2026-02-08 `[CODE]` Added monorepo scaffold (`api/`, `workers/`, `web/`, `db/`) and bootstrap configs.
- 2026-02-08 `[CODE]` Added baseline DB schema + migration + seed script.
- 2026-02-08 `[CODE]` Added FastAPI skeleton endpoints and worker polling scaffold.

## Working set
- 2026-02-08 `[CODE]` API and workers still use in-memory/job-client bootstrap flow pending DB wiring.
- 2026-02-08 `[ASSUMPTION]` Target stack remains Next.js + FastAPI + Supabase + Cloud Run per handoff spec.
- 2026-02-08 `[ASSUMPTION]` Build/test/lint/typecheck commands are provisionally mapped via root `Makefile`.

## Decisions
- 2026-02-08 `[CODE]` D-001 and D-002 active in `.agent/DECISIONS.md`.

## Receipts
- 2026-02-08 `[TOOL]` `find .. -maxdepth 3 -type d -name handoff` located `../tmpl-starter/handoff`.
- 2026-02-08 `[TOOL]` `cp ../tmpl-starter/handoff/* handoff/` imported transfer docs.
- 2026-02-08 `[TOOL]` Created initial project files in `api/`, `workers/`, `web/`, `db/`, and `docs/`.
