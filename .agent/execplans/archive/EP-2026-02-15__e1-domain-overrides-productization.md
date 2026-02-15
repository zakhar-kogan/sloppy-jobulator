# EP-2026-02-15__e1-domain-overrides-productization

- Status: ARCHIVED
- Created: 2026-02-15
- Updated: 2026-02-15
- Archived: 2026-02-15
- Owner: Codex
- Depends on: EP-2026-02-08__bootstrap-foundation-v1, EP-2026-02-12__env-bindings-e2-h2l1

## Objective
Complete E1 per-domain URL normalization override contract end-to-end so override behavior is productized through persisted admin-managed policy, shared by ingest normalization and redirect-resolution worker paths.

## Scope
1. DB schema + repository contract for URL normalization overrides (read/update/enable toggle).
2. Admin API endpoints + validation + audit provenance events.
3. Shared persisted override source for `/discoveries` normalization and redirect job execution behavior.
4. DB-backed integration tests for precedence and rollback semantics.
5. One admin live E2E proving override mutation changes observable seeded discovery normalization outcome.

## Out of Scope
1. New auth roles/permissions beyond existing `admin:write`.
2. Broad cockpit redesign; only contract-complete UI/API wiring for override management.

## Risks and Mitigations
1. Risk: queued redirect jobs using stale override snapshot.
- Mitigation: hydrate redirect job inputs from persisted override source at claim-time.
2. Risk: invalid override payloads causing silent normalization drift.
- Mitigation: strict repository validation + explicit 422 messaging + integration assertions.
3. Risk: regressions to existing redirect or trust-policy paths.
- Mitigation: target existing suites plus new focused tests.

## Validation Plan
1. `uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "url_normalization_override or redirect_resolution"`
2. `uv run --project workers --extra dev pytest workers/tests/test_redirects.py`
3. `fnm exec --using 24.13.0 pnpm --dir web test:e2e:live --grep "override mutation"`

## Rollback Plan
1. Disable override rows via admin PATCH if behavior is incorrect.
2. Revert migration + repository/API/UI commit if contract issues are discovered.

## Outcome
Completed: persisted per-domain override contract now spans DB, admin API/UI, ingest normalization, redirect-claim hydration, DB-backed precedence/rollback coverage, and one live admin mutation-effect E2E.
