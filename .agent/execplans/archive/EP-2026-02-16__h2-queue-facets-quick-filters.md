# Plan ID: EP-2026-02-16__h2-queue-facets-quick-filters

- Status: `DONE`
- Created: `2026-02-16`
- Last Updated: `2026-02-16`
- Owner: `Codex`

## Purpose / Big Picture
Ship the next concrete H2 cockpit speed increment by adding queue facets/counts (`state`, `source`, `age`) and one-click quick filter chips so moderators can narrow the queue in fewer steps.

## Scope and Constraints
- In scope:
  - API support for candidate queue facets.
  - Cockpit quick-filter chips and state wiring for facet filters.
  - Targeted tests for new behavior.
- Out of scope:
  - Keyboard batch flow (`j/k`, select, patch/override).
  - Discovery ranking or public posting detail work.
- Constraints:
  - Keep existing candidate list endpoint shape stable.
  - Preserve existing moderation transition guardrails and bulk actions.
  - Keep changes small/reviewable and validate with relevant checks.

## Progress
- [x] Clarify scope and current queue architecture.
- [x] Implement backend facets endpoint and repository aggregation.
- [x] Add web admin proxy route/types for facets.
- [x] Add cockpit quick-filter chips and filter interactions.
- [x] Run targeted tests and capture receipts.

## Decision Log
- 2026-02-16: Implement facets via a dedicated endpoint instead of changing `GET /candidates` list payload, to avoid compatibility risk with existing clients/tests.

## Plan of Work
1. API + repository facets
   - Touched paths: `api/app/schemas/candidates.py`, `api/app/services/repository.py`, `api/app/api/routes/candidates.py`
   - Deliverable: `GET /candidates/facets` returning grouped counts for state/source/age.
2. Web proxy + cockpit model
   - Touched paths: `web/lib/admin-cockpit.ts`, `web/lib/admin-proxy-paths.ts`, `web/app/api/admin/candidates/facets/route.ts`
   - Deliverable: typed fetch path and route forwarding for facets.
3. Cockpit UI quick filters
   - Touched path: `web/app/admin/cockpit/moderator-cockpit-client.tsx`
   - Deliverable: facet chips with count badges that apply filters in one click.
4. Tests
   - Touched paths: `api/tests/test_discovery_jobs_integration.py`, `web/tests/admin-proxy-paths.test.ts`
   - Deliverable: coverage for endpoint contract and proxy path generation.

## Validation and Acceptance
- `uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k candidate_facets`
  - Expect: facet endpoint returns deterministic grouped counts and honors filters.
- `fnm exec --using 24.13.0 pnpm --dir web test -- admin-proxy-paths.test.ts`
  - Expect: new facets path mapping passes.

## Idempotence and Recovery
- Changes are additive (new endpoint/route/types) and reversible by removing new code paths.
- If facet query has issues, cockpit can continue to function using existing manual filters without data mutation risk.

## Outcomes and Retrospective
- Added `GET /candidates/facets` plus optional `source`/`age` filters on candidate listing and wired cockpit quick-filter chips with queue counts.
- Validation passed for authz, integration, contracts, and web typecheck with DB-backed run executed via escalation when sandbox blocked localhost DB access.
