# Task
- Request: Continue H2 cockpit hardening + L1 moderation/admin E2E expansion on follow-up branch.
- Scope: Add bounded limit guardrails and expand mock/live coverage with additional persistence assertions.

## Actions Taken
1. Added bounded integer coercion helper for admin UI query/maintenance limits.
2. Wired candidate/module/job/maintenance limit inputs to clamp to backend contract bounds before dispatch.
3. Expanded mock and live Playwright coverage for clamp behavior and persistence-oriented guardrail checks.

## What Went Wrong
1. Live guardrail test flaked because selected candidate drifted in a dense queue.
- Root cause: assertions assumed selection persisted without reselecting target row.
- Prevention rule: reselect/verify target candidate context before mutation assertions in queue-like UIs.

## What Went Right
1. UI bounds now align with API limit contracts and are validated at utility + browser levels.
- Evidence: contracts/typecheck + mock (5/5) + live (4/4) Playwright passing.

## Reusable Learnings
1. Validate numeric filter constraints at both helper and end-to-end UI request layers.
- Promotion decision: `promote now`
- Promote to: `PATTERNS.md`

## Receipts
- Commands: `pnpm --dir web test:contracts`, `pnpm --dir web typecheck`, mock/live Playwright suites.
- Files changed: cockpit client + admin utils + tests.
