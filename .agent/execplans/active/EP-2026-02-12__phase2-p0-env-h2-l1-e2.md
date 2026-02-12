# ExecPlan: EP-2026-02-12__phase2-p0-env-h2-l1-e2

## Metadata
- Status: `ACTIVE`
- Created: `2026-02-12`
- Updated: `2026-02-12`
- Owner: `Codex`

## Purpose / Big Picture
Execute the next implementation-plan sequence in one branch: finish environment bindings for `J1/J2/M1`, continue `H2` cockpit hardening, expand `L1` moderation/admin E2E coverage, and start `E2` redirect-resolution async execution.

## Scope and Constraints
- In scope:
1. M1 deploy execution workflow wiring behind current CI readiness gate.
2. J1/J2 environment binding docs/templates for OTLP + Cloud Monitoring imports/notification channels.
3. H2 cockpit guardrail hardening that preserves current API contracts.
4. L1 expansion covering new cockpit guardrails in mock + live Playwright suites.
5. E2 v0: `resolve_url_redirects` worker handling + API-side result application into discovery canonical fields, with controlled enqueue rollout.
- Out of scope:
1. Full production credentials/secrets provisioning.
2. Per-domain URL normalization overrides (E1 follow-up).
3. Full E2 rollout without feature-flag control.
- Constraints:
1. Keep machine-readable API contracts stable unless explicitly expanded.
2. Keep ingestion path non-blocking; redirect resolution remains async only.
3. Preserve compatibility with existing DB-backed integration and live E2E suites.

## Progress
- [x] Add M1 environment-specific deploy execution workflow + documentation.
- [x] Add J1/J2 observability environment bindings documentation/templates.
- [x] Implement H2 cockpit maintenance-action confirmation guardrail.
- [x] Expand L1 Playwright mock/live tests for new guardrail behavior.
- [x] Implement E2 worker redirect-resolution execution + repository result-apply path.
- [x] Add E2 tests (worker unit + API DB integration) and run validation commands.

## Decision Log
- 2026-02-12: Sequence execution follows roadmap order (`J1/J2/M1` -> `H2` -> `L1` -> `E2`) while keeping each track reversible and independently testable.
- 2026-02-12: E2 enqueue path starts behind a config flag to avoid destabilizing current extraction-first ingest behavior during rollout.

## Plan of Work
1. Environment bindings and deploy execution
- Paths: `.github/workflows/`, `docs/observability/`, `.agent/RUNBOOK.md`, `README.md`.
2. Cockpit hardening and E2E expansion
- Paths: `web/app/admin/cockpit/moderator-cockpit-client.tsx`, `web/tests-e2e/*.spec.ts`.
3. E2 start implementation
- Paths: `api/app/core/config.py`, `api/app/api/routes/discoveries.py`, `api/app/services/repository.py`, `workers/app/jobs/*`, `workers/app/jobs/executor.py`, `workers/app/core/config.py`.
4. Validation and capture
- Commands: targeted pytest/playwright + lint/typecheck/hygiene checks.

## Validation and Acceptance
1. `uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "redirect or enqueue or discovery"`
- Expected: redirect-related integration tests pass with existing baseline tests unaffected.
2. `uv run --project workers --extra dev pytest workers/tests`
- Expected: worker tests pass including new redirect-resolution coverage.
3. `fnm exec --using 24.13.0 pnpm --dir web test:e2e`
- Expected: mocked cockpit E2E passes with new guardrail assertions.
4. `fnm exec --using 24.13.0 pnpm --dir web typecheck`
- Expected: no TS regressions in cockpit UI changes.
5. `bash scripts/agent-hygiene-check.sh --mode project`
- Expected: agent contract checks pass.

## Idempotence and Recovery
1. Deploy workflow is additive and can be disabled by reverting a single workflow file.
2. E2 enqueue behavior is flag-gated (`disabled` default) for safe staged rollout.
3. Redirect result-apply logic only mutates discovery URL/canonical fields when a valid resolved URL is present.

## Outcomes and Retrospective
- Outcome: `DONE`
- Follow-ups:
1. Promote E2 enqueue flag to default-on after staging validation of redirect behavior and extract replay impact.
2. Tune deploy workflow to concrete environment names/secrets once production bindings are finalized.
