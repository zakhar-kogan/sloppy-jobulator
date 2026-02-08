# Decisions

Use ADR-lite entries:
- ID: `D-###`
- Status: `ACTIVE | SUPERSEDED`
- Date: `YYYY-MM-DD`
- Decision:
- Why:
- Impact:

## Decision Log

### D-001 (Adopt monorepo service split from day one)
- Status: ACTIVE
- Date: 2026-02-08
- Decision: Create `api/`, `workers/`, `web/`, and `db/` now, instead of implementing in a single service first.
- Why: The handoff contracts already separate concerns by runtime and auth model; collapsing them early would increase rework.
- Impact: Each workstream can progress independently while keeping explicit API/database contracts.

### D-002 (Implement DB-first contracts with in-memory app bootstrap)
- Status: ACTIVE
- Date: 2026-02-08
- Decision: Ship initial endpoints and worker loop against in-memory stores while committing the canonical Postgres schema/migration baseline.
- Why: This gives immediate executable surfaces without blocking on full Supabase wiring.
- Impact: Near-term iteration speed improves, with explicit follow-up to replace temporary stores with repository-backed persistence.
