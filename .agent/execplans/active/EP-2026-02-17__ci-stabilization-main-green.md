Plan ID: EP-2026-02-17__ci-stabilization-main-green
Status: ACTIVE
Created: 2026-02-17
Last Updated: 2026-02-17
Owner: Codex

## Purpose / Big Picture
Stabilize `main` CI after worker timeout bugfix by addressing currently failing suites (`api-integration-db`, `web-e2e-live`) without changing intended product behavior.

## Scope and Constraints
- Scope: API trust-policy rules validation path and live E2E expectations for admin cockpit maintenance/patch flows.
- Constraints: Keep admin 80/20 trust-policy surface minimal; avoid schema or contract breaks; prefer small testable diffs.

## Progress
- [x] Confirmed current CI failures and compared with previous run for regression isolation.
- [ ] Implement API validation fix for accepted/sanitized advanced trust-policy keys.
- [ ] Re-run targeted DB integration slice.
- [ ] Align/stabilize failing live E2E tests with current cockpit behavior.
- [ ] Re-run live E2E suite and summarize risk.

## Decision Log (what changed, why, date)
- 2026-02-17: Treat pre-existing CI red as baseline debt; fix now in same stream to restore green after worker bugfix push.

## Plan of Work (concrete steps and touched paths)
1. Patch `api/app/services/repository.py` trust-policy rules validator to:
   - accept known advanced keys,
   - validate nested map keys/values,
   - sanitize storage output to current minimal policy profile.
2. Update `web/tests-e2e/admin-cockpit.live.spec.ts`:
   - remove stale UI expectation for reap button path,
   - rely on backend state poll for pagination patch success (reduce toast flake sensitivity).
3. Run:
   - DB-backed trust-policy integration subset.
   - live cockpit E2E spec.

## Validation and Acceptance (commands + expected outcomes)
- `make db-up && make db-reset`
- `SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k trust_policy -q`
- `SJ_DATABASE_URL=... DATABASE_URL=... fnm exec --using 24.13.0 pnpm --dir web test:e2e:live`
- Expected: no failures in previously failing trust-policy and cockpit live scenarios.

## Idempotence and Recovery
- Changes are code/test-only and reversible by commit rollback.
- If targeted validation fails, isolate by suite and revert only destabilizing test assumptions first.

## Outcomes and Retrospective
- Pending execution.
