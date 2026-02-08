# Runbook

## Setup and local run
1. Install dependencies: `UNCONFIRMED`
2. Start local services: `UNCONFIRMED`
3. Run app locally: `UNCONFIRMED`

## Build/test/quality
1. Build: `UNCONFIRMED`
2. Test: `UNCONFIRMED`
3. Lint: `UNCONFIRMED`
4. Typecheck: `UNCONFIRMED`
5. Required pre-finalization checks (fill with concrete commands): `UNCONFIRMED`

## Database operations
1. Migration command: `UNCONFIRMED`
2. Seed command: `UNCONFIRMED`
3. Rollback/recovery: `UNCONFIRMED`

## Incident basics
1. Health check endpoint/command: `UNCONFIRMED`
2. Log query path: `UNCONFIRMED`
3. Rollback command/path: `UNCONFIRMED`

## Agentic framework maintenance
1. Set workflow mode explicitly:
- Template repo: `--mode template` (sanitized scaffold only).
- Downstream project repo: `--mode project` (full task-state capture).
2. For substantial tasks, run a balanced review:
- What went wrong, why, prevention?
- What went right, measurable improvement, reusable or not?
3. Triage each item as `promote now | pilot backlog | keep local`.
4. In `project` mode, update notes/helpers/continuity and promote high-leverage items.
5. In `template` mode, do not record live task state; only improve reusable template policy/docs/scripts.
6. Weekly hygiene: prune stale notes, deduplicate conflicting guidance, and update `UNCONFIRMED` commands when known.
7. Run contract checks: `bash scripts/agent-hygiene-check.sh --mode template|project`.
8. Run weekly maintenance review: `bash scripts/agent-weekly-review.sh --mode template|project`.
