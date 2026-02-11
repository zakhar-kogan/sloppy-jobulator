# Task
- Request: Proceed with implementation-plan next steps `H2` cockpit hardening and `L1` moderation/admin E2E expansion.
- Scope: Add operator guardrails/ergonomic improvements in `/admin/cockpit` while preserving API contracts; extend mock/live Playwright coverage for those guardrails.
- Constraints: Keep changes reviewable, avoid API/schema contract churn, validate with web contracts/typecheck and Playwright (mock + live).

## Actions Taken
1. Added shared client-side transition helpers in `web/lib/admin-cockpit-utils.ts` (`canTransitionCandidateState`, `listPatchCandidateStates`) mirroring backend patch-transition rules.
2. Hardened cockpit UI in `web/app/admin/cockpit/moderator-cockpit-client.tsx`:
- patch state options now constrained by selected candidate transition bounds;
- destructive patch states (`rejected|archived|closed`) require reason;
- merge/override require reason before submit;
- added quick-pick merge candidate selector from current queue;
- reset form fields after successful actions.
3. Expanded tests:
- Contract tests for transition helper behavior (`web/tests/admin-cockpit-utils.test.ts`);
- Mock Playwright guardrail coverage (`web/tests-e2e/admin-cockpit.spec.ts`);
- Live Playwright guardrail coverage (`web/tests-e2e/admin-cockpit.live.spec.ts`).

## What Went Wrong
1. Issue: New mock Playwright guardrail tests initially failed.
- Root cause: Existing merge self-check test clicked a now-disabled button (reason-required guardrail), and transition-option assertions ran before candidate selection state was hydrated.
- Early signal missed: First red run showed disabled merge button timeout and all-state patch options.
- Prevention rule: When guardrails add submit-disable conditions, update legacy tests to satisfy new prerequisites and wait for selected-candidate hydration before asserting form option sets.

## What Went Right
1. Improvement: Backend transition rules are now mirrored in a shared UI utility with direct contract tests.
- Evidence (time/readability/performance/manageability/modularity): Removed ad-hoc transition assumptions from component logic; tests now pin transition behavior in one place and reduce drift risk.
- Why it worked: Utility-first extraction made UI and tests consume the same rule set.
2. Improvement: Added live E2E assertions for reason/transition guardrails.
- Evidence (time/readability/performance/manageability/modularity): Live suite now covers one additional operator-guardrail scenario (`4/4` live tests passing) without adding runtime plumbing complexity.
- Why it worked: Scenario reused existing discovery/job seeding helpers and asserted both UI gating and DB-observable candidate state.

## Reusable Learnings
1. Learning: Mirror backend transition contracts in a shared frontend helper and drive UI option sets from that helper rather than hardcoding full enums.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `PATTERNS.md`
- Why: Prevents frontend/backend policy drift and turns transition changes into single-surface updates with direct tests.
2. Learning: Guardrail UI changes should be treated as behavior changes in E2E, not only component-level UX tweaks.
- Promotion decision: `keep local`
- Promote to (if `promote now`): `UNCONFIRMED`
- Why: Valuable for this cockpit flow; broader generalization needs more repetition across other admin surfaces.

## Receipts
- Commands run:
- `fnm exec --using 24.13.0 pnpm --dir web test:contracts`
- `fnm exec --using 24.13.0 pnpm --dir web typecheck`
- `(escalated) fnm exec --using 24.13.0 pnpm --dir web exec playwright test tests-e2e/admin-cockpit.spec.ts`
- `make db-up -> make db-reset -> (escalated) UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... fnm exec --using 24.13.0 pnpm --dir web test:e2e:live -> make db-down`
- Files changed:
- `web/app/admin/cockpit/moderator-cockpit-client.tsx`
- `web/lib/admin-cockpit-utils.ts`
- `web/tests/admin-cockpit-utils.test.ts`
- `web/tests-e2e/admin-cockpit.spec.ts`
- `web/tests-e2e/admin-cockpit.live.spec.ts`
- Tests/checks:
- Web contracts pass (`15/15`)
- Web typecheck pass
- Mock Playwright cockpit suite pass (`4/4`)
- Live Playwright cockpit suite pass (`4/4`)
