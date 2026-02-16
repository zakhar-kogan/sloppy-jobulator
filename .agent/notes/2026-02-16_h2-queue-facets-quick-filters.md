# Task
- Request: Execute the next concrete product build item for H2 cockpit triage speed with queue facets/counts and quick filters.
- Scope: Add candidate queue facets (`state`, `source`, `age`), one-click cockpit filter chips, and required backend/web contract wiring.
- Constraints: Keep existing list contract stable, preserve moderation guardrails, validate with targeted checks.

## Actions Taken
1. Added candidate facet contracts and API route: `GET /candidates/facets` with optional `state`/`source`/`age` filters.
2. Extended repository list query filters to include `source` and `age` and added facet aggregation query for state/source/age counts.
3. Added web proxy route/path helpers/types and cockpit quick-filter UI chips with facet count badges plus reset flow.
4. Added/updated authz, integration, and web contract tests; validated with DB-backed targeted pytest and web typecheck.

## What Went Wrong
1. DB-backed integration test failed in sandbox due localhost socket restrictions and uv cache access.
- Root cause: sandbox restrictions blocked `~/.cache/uv` and local Postgres socket access.
- Early signal missed: first integration run error clearly indicated sandbox/network boundary.
- Prevention rule: for DB-backed pytest in Codex sandbox, default to `UV_CACHE_DIR=/tmp/uv-cache` and escalate promptly when localhost access is denied.

## What Went Right
1. Added facets as a dedicated endpoint without breaking existing candidate list response shape.
- Evidence (time/readability/performance/manageability/modularity): minimal client break risk, additive route/proxy wiring, targeted tests remained focused and passed.
- Why it worked: separation of concerns between list payload and analytics/facet payload.

## Reusable Learnings
1. Keep list endpoints stable and ship additive facet endpoints when introducing cockpit analytics/counts.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `PATTERNS.md`
- Why: lowers regression risk while enabling faster operator UX iteration.

2. DB-backed test execution in Codex sandbox should frontload cache override + escalation fallback.
- Promotion decision: `keep local`
- Why: helper already exists (`H-2026-02-10__db-integration-escalation`), no net-new pattern needed.

## Receipts
- Commands run: `uv run --project api --extra dev pytest api/tests/test_candidates_authz.py -q`; `fnm exec --using 24.13.0 pnpm --dir web run test:contracts -- admin-proxy-paths.test.ts`; `make db-up`; `make db-reset`; `/bin/zsh -lc "UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k candidates_facets_include_state_source_and_age_counts -q"`; `fnm exec --using 24.13.0 pnpm --dir web run typecheck`; `make db-down`.
- Files changed: API candidate schemas/routes/repository + integration/authz tests; web proxy paths/route/types + cockpit client/CSS + proxy path tests; `.agent` plan/index/notes artifacts.
- Tests/checks: authz pytest passed, targeted DB-backed integration pytest passed, web contract tests passed, web typecheck passed.
