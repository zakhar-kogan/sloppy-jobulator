# ExecPlan: EP-2026-02-16__completion-checklist-p0-launch

## Metadata
- Status: `ACTIVE`
- Created: `2026-02-16`
- Updated: `2026-02-16`
- Owner: `Codex`

## Objective
Drive remaining launch-critical in-progress items (`G1`, `F2`, `L1`, `J1`, `J2`, `M1`) to completion with explicit acceptance checks and no new feature scope.

## Scope
- In scope:
1. Close API/query edge hardening and product usability gaps in `G1/H1` without introducing new domain features.
2. Close remaining policy-path and contract hardening in `F2`.
3. Stabilize full regression posture for `L1` (DB-backed integration + live cockpit reliability).
4. Complete environment-bound observability/deploy validation tasks for `J1/J2/M1`.
- Out of scope:
1. New connector families (`K*`) and LLM router work (`I*`).
2. Load testing (`L2`) and post-launch runbook expansion (`M2`) unless required by a blocker.

## Constraints
1. Preserve existing API compatibility unless a change is required to fix a correctness issue.
2. Prefer small, reviewable diffs with test receipts after each closure item.
3. Keep checklist order aligned to launch risk: correctness -> reliability -> deploy safety.

## Plan
1. `G1/H1` query semantics + usability hardening
- Deliverable: finalize postings filter/sort/search edge handling and public catalogue behavior against real API bounds.
- Validation: targeted `api/tests/test_discovery_jobs_integration.py -k postings` + `pnpm --dir web test:contracts` + `pnpm --dir web typecheck`.

2. `F2` trust-policy residual closure
- Deliverable: confirm merge-action/moderation-route rule coverage and any missing guardrail contracts/tests.
- Validation: `api/tests/test_discovery_jobs_integration.py -k trust_policy` plus static checks.

3. `L1` reliability hardening
- Deliverable: stable end-to-end regression path for moderation/admin flows with deterministic live + mock receipts.
- Validation: `pnpm --dir web exec playwright test web/tests-e2e/admin-cockpit.spec.ts` + `pnpm --dir web test:e2e:live` + targeted DB-backed API integration slice.

4. `J1/J2` environment observability bind
- Deliverable: execute staged telemetry quality checks and dashboard/alert binding with environment-backed values.
- Validation: `scripts/validate-telemetry-quality.sh` + `scripts/import-observability-assets.sh` with non-placeholder inputs.

5. `M1` deploy-readiness execution proof
- Deliverable: run deploy-readiness gate path with all required checks green and documented receipts.
- Validation: CI evidence (`migration-safety`, `web-e2e-live`, `deploy-readiness-gate`) linked in continuity.

## Risks and Mitigations
1. Risk: Live E2E intermittency obscures real regressions.
- Mitigation: re-run from clean DB state and pin assertions to deterministic setup data.
2. Risk: Environment-bound observability tasks blocked by missing secrets/channel IDs.
- Mitigation: track exact missing bindings as explicit blockers and keep non-bound assets validated.

## Execution Log
- `2026-02-16`: Plan created; baseline indicates `L1` live E2E and DB-backed slices are currently runnable and passing when executed from a clean reset state.

## Closeout
- Outcome: `IN_PROGRESS`
- Follow-ups:
1. Archive after `G1/F2/L1/J1/J2/M1` status table rows can be marked done with receipts.
- Archive action: move this file to `/.agent/execplans/archive/` and update `/.agent/execplans/INDEX.md`.
