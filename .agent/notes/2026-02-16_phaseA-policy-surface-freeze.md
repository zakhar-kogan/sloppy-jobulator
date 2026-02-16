# Task
- Request: Execute Phase A of 80/20 simplification: freeze source trust policy surface and hide advanced controls.
- Scope: simplify admin trust-policy UI and enforce minimal backend defaults in admin route.
- Constraints: keep core admin CRUD flow working and validate with DB-backed integration coverage.

## Actions Taken
1. Simplified source trust policy admin form to minimal controls (`source_key`, `trust_level`, `auto_publish`, `enabled`) and removed editable `requires_moderation`/`rules_json` fields.
2. Updated admin trust-policy PUT route to normalize payload into a simple profile:
   - `auto_publish` forced false for `untrusted`.
   - `requires_moderation` derived as inverse of effective auto-publish.
   - `rules_json` forced to `{}`.
3. Updated admin trust-policy integration tests to assert normalized behavior.
4. Ran web typecheck and DB-backed targeted integration tests for admin trust-policy flows.

## What Went Wrong
1. Initial DB reset after compose startup failed with a transient service readiness race.
- Root cause: `make db-reset` executed before compose service became fully ready.
- Early signal missed: immediate post-start reset call.
- Prevention rule: on fresh `make db-up`, rerun reset once on transient service-not-running error before escalating.

## What Went Right
1. Route-level normalization let us de-scope admin surface without touching deeper repository policy machinery yet.
- Evidence (time/readability/performance/manageability/modularity): small diff, targeted test updates, preserved existing repository contracts for later phased cleanup.
- Why it worked: boundary enforcement at admin API ingress keeps risk localized.

## Reusable Learnings
1. For de-scope phases, normalize complexity at API boundaries first before deleting deep internals.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `PATTERNS.md`
- Why: enables low-risk staged simplification.

## Receipts
- Commands run:
  - `fnm exec --using 24.13.0 pnpm --dir web run typecheck`
  - `make db-up`
  - `make db-reset` (transient fail then pass)
  - `(escalated) /bin/zsh -lc "UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k admin_source_trust_policy -q"`
  - `make db-down`
- Files changed:
  - `web/app/admin/source-trust-policy/source-trust-policy-admin.tsx`
  - `api/app/api/routes/admin.py`
  - `api/tests/test_discovery_jobs_integration.py`
  - `/.agent/execplans/active/EP-2026-02-16__80-20-descope-simplification.md`
- Tests/checks:
  - `4 passed, 44 deselected` (admin source-trust-policy DB-backed integration slice).
  - web `tsc --noEmit` passed.
