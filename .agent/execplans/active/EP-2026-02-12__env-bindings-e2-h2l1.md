# ExecPlan: EP-2026-02-12__env-bindings-e2-h2l1

## Metadata
- Status: `ACTIVE`
- Created: `2026-02-12`
- Last Updated: `2026-02-15`
- Owner: `Codex`

## Purpose / Big Picture
Close the current critical backlog by wiring environment-bound staging/prod observability+deploy execution (J1/J2/M1), expanding moderation/admin E2E breadth (H2/L1), and shipping an incremental async redirect-resolution path with deeper semantics (E2).

## Scope and Constraints
- In scope:
1. Add `ENVIRONMENT_BINDINGS` contract and deployment workflow wiring for staging/prod.
2. Add observability binding/import and telemetry quality validation scripts.
3. Expand cockpit E2E coverage for queue/filter/pagination and cross-flow operator paths.
4. Implement incremental `resolve_url_redirects` worker execution + API persistence path and tests.
- Out of scope:
1. Full infra provisioning for Cloud Run/Vercel/Supabase.
2. Final E1 per-domain override productization across all services.
3. Full production traffic validation and threshold retuning.
- Constraints:
1. Preserve existing API contracts and current CI gates.
2. Keep redirect resolution asynchronous and off ingest critical path.
3. Keep changes reviewable and reversible by area (docs/workflow, API/workers, tests).

## Progress
- [x] Add environment bindings + deploy workflow baseline for staged deploy execution.
- [x] Add J1/J2 scripts for telemetry sink/quality validation and dashboard+alert policy import bindings.
- [x] Implement E2 redirect-resolution execution semantics in workers and persistence handling in API repository.
- [x] Expand H2/L1 Playwright moderation/admin coverage for queue/filter/pagination cross-flow.
- [x] Run targeted validation matrix and capture continuity notes.

## Decision Log
- 2026-02-12: Keep deploy workflow command-driven via environment-bound secrets to avoid hardcoding provider-specific deploy mechanics before infra commands are finalized.
- 2026-02-12: Gate redirect job enqueue behind explicit discovery metadata signal for incremental rollout without perturbing existing ingest contract tests.
- 2026-02-12: Added shared URL-normalization override semantics in API and workers (`strip_www`, `force_https`, custom query stripping) to align redirect resolution with eventual E1 per-domain policy support.
- 2026-02-15: Promote redirect enqueue decisioning to settings-default + per-event metadata override semantics, and pass settings normalization override JSON through redirect job inputs so worker-side normalization stays aligned with E1 policy behavior.
- 2026-02-15: Expand cockpit L1 breadth with selection-retarget cross-flow tests so moderation mutations track the active filtered row after queue page/filter changes.

## Plan of Work
1. Environment bindings + staged deploy workflow
- Deliverables: `docs/ENVIRONMENT_BINDINGS.md`, `.github/workflows/deploy.yml`.
- Paths: `docs/ENVIRONMENT_BINDINGS.md`, `.github/workflows/deploy.yml`.
2. Observability binding and sink validation
- Deliverables: scripts to bind/import dashboard+alerts and run telemetry quality checks.
- Paths: `scripts/bind-observability-assets.py`, `scripts/import-observability-assets.sh`, `scripts/validate-telemetry-quality.sh`, `docs/observability/*`.
3. Redirect-resolution E2 increment
- Deliverables: worker redirect resolver + executor routing + repository result application + integration/unit tests.
- Paths: `workers/app/jobs/*`, `workers/tests/*`, `api/app/services/repository.py`, `api/tests/test_discovery_jobs_integration.py`.
4. H2/L1 E2E breadth expansion
- Deliverables: additional cockpit Playwright scenarios for queue/filter/pagination cross-flow.
- Paths: `web/tests-e2e/admin-cockpit.spec.ts`, `web/tests-e2e/admin-cockpit.live.spec.ts`.

## Validation and Acceptance
1. `uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k redirect`
- Expected: redirect integration coverage passes.
2. `uv run --project workers --extra dev pytest workers/tests`
- Expected: worker job semantics tests pass including redirect resolver coverage.
3. `fnm exec --using 24.13.0 pnpm --dir web exec playwright test web/tests-e2e/admin-cockpit.spec.ts`
- Expected: expanded mock cockpit coverage passes.
4. `make lint && make typecheck`
- Expected: no regressions in static checks.

## Idempotence and Recovery
1. Observability/deploy scripts are additive and environment-driven; rollback is file-level revert.
2. Redirect resolution remains asynchronous; enqueue behavior is controllable via `SJ_ENABLE_REDIRECT_RESOLUTION_JOBS` with per-event metadata override for scoped rollback.
3. E2E expansions are test-only and can be reverted independently if flaky.

## Outcomes and Retrospective
- Outcome: `IN_PROGRESS`
- Follow-ups:
1. Promote metadata-gated redirect enqueue to default once production behavior and E1 override contract are finalized.
2. Replace command-driven deploy secret hooks with explicit Cloud Run/Vercel deploy steps when infra commands are confirmed.
