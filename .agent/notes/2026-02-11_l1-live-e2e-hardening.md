# Task
- Request: Execute remaining L1 queue items: live negative/authz cockpit coverage, persistence-depth assertions, CI runtime hardening, proxy failure-mapping contracts, and PR-ready summary.
- Scope: `web/tests-e2e`, `web/tests`, `web/lib`, `.github/workflows/ci.yml`, roadmap/continuity/execplan capture.
- Constraints: Preserve API contracts; keep retries scoped; validate with project commands.

## Actions Taken
1. Expanded live Playwright cockpit tests with negative/authz coverage and conflict-path UI assertion.
2. Added persistence-depth assertions for candidate events, module mutation timestamps, and jobs enqueue/reap state transitions.
3. Hardened `web-e2e-live` CI job with uv/pnpm/Playwright caching, explicit timeout budgets, and scoped retry-once only for the live E2E step.
4. Refactored admin proxy forwarding into `web/lib/admin-api-core.ts` and kept Next wrapper behavior in `web/lib/admin-api.ts`.
5. Added `node:test` API-contract coverage for admin proxy failure mapping in `web/tests/admin-proxy-failure-mapping.test.ts`.
6. Produced PR-ready test matrix + known-risk summary in `docs/roadmap/L1_E2E_PR_SUMMARY_2026-02-11.md`.
7. Updated continuity/execplan/roadmap status to reflect completed queue items and next handoff focus.

## What Went Wrong
1. Issue: Early persistence assertions in live E2E were brittle (freshness enqueue expected a specific posting job).
- Root cause: freshness job selection is order/data dependent in shared DB state.
- Early signal missed: repository query logic orders due postings and can validly enqueue different postings.
- Prevention rule: assert state deltas and backend-returned counts rather than fixed entity IDs for queue maintenance actions.
2. Issue: Contract tests initially attempted importing Next route modules directly in `node:test`.
- Root cause: `node --test` environment could not resolve `next/server` and extensionless route imports.
- Early signal missed: existing contract tests only target framework-agnostic modules.
- Prevention rule: isolate runtime-agnostic logic in plain modules (`*-core.ts`) and test those in `node:test`; keep thin framework wrappers separately.
3. Issue: Selector assumptions for jobs maintenance panel caused avoidable timeouts.
- Root cause: test looked for non-existent heading label.
- Early signal missed: panel heading text differed from assumed copy.
- Prevention rule: use stable control labels/roles (`getByLabel`, `getByRole`) over inferred heading containers where possible.

## What Went Right
1. Improvement: CI runtime variance reduced by cache-backed setup and explicit budgets.
- Evidence (time/readability/performance/manageability/modularity): live suite reran in ~19s after browser/dependency cache warmup; job now has bounded per-step and overall budgets.
- Why it worked: moved from implicit environment assumptions to explicit dependency + browser provisioning and scoped retry.
2. Improvement: Proxy failure mapping is now contract-tested without framework coupling.
- Evidence (time/readability/performance/manageability/modularity): `test:contracts` increased to `13/13` with new passthrough/error-shape assertions.
- Why it worked: extracted pure forwarding core enabled deterministic unit contracts.
3. Improvement: Live cockpit assertions now validate persistence invariants beyond UI toast messages.
- Evidence (time/readability/performance/manageability/modularity): live E2E verifies candidate events + module `updated_at` + jobs requeue lock/lease reset.
- Why it worked: combined UI actions with direct API reads for backend-observable outcomes.

## Reusable Learnings
1. Learning: For queue-like admin actions, verify delta invariants (`after - before == returned count`) instead of hardcoded target identities.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `PATTERNS.md`
- Why: avoids false negatives from legitimate ordering/data variation while preserving correctness.
2. Learning: Keep Next.js route wrappers minimal and centralize proxy logic in framework-agnostic modules to unblock `node:test` contract coverage.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `PATTERNS.md`
- Why: improves testability and portability without changing runtime contracts.
3. Learning: Scope retries at CI step level for known flaky process startup; avoid global per-test retries for deterministic failures.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `RUNBOOK.md`
- Why: keeps failure signals actionable while still handling transient startup noise.

## Receipts
- Commands run:
  - `fnm exec --using 24.13.0 pnpm --dir web test:e2e:live` (multiple iterations; final `3/3` pass)
  - `fnm exec --using 24.13.0 pnpm --dir web test:contracts` (`13/13` pass)
  - `fnm exec --using 24.13.0 pnpm --dir web typecheck` (pass)
  - `bash scripts/agent-hygiene-check.sh --mode project` (pass)
  - `(escalated) fnm exec --using 24.13.0 pnpm --dir web exec playwright install chromium`
- Files changed:
  - `web/tests-e2e/admin-cockpit.live.spec.ts`
  - `.github/workflows/ci.yml`
  - `web/playwright.live.config.ts`
  - `web/lib/admin-api-core.ts`
  - `web/lib/admin-api.ts`
  - `web/tests/admin-proxy-failure-mapping.test.ts`
  - `docs/roadmap/L1_E2E_PR_SUMMARY_2026-02-11.md`
  - `.agent/CONTINUITY.md`
  - `.agent/execplans/active/EP-2026-02-08__bootstrap-foundation-v1.md`
  - `docs/roadmap/IMPLEMENTATION_PLAN_v1.2.md`
- Tests/checks:
  - `pnpm --dir web test:e2e:live`: pass (`3/3`)
  - `pnpm --dir web test:contracts`: pass (`13/13`)
  - `pnpm --dir web typecheck`: pass
  - `bash scripts/agent-hygiene-check.sh --mode project`: pass
