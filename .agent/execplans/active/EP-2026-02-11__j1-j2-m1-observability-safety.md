# ExecPlan: EP-2026-02-11__j1-j2-m1-observability-safety

## Metadata
- Status: `ACTIVE`
- Created: `2026-02-11`
- Updated: `2026-02-11`
- Owner: `Codex`

## Purpose / Big Picture
Deliver Phase-4 observability and deploy-safety baseline by implementing OpenTelemetry instrumentation for API/workers/client+DB paths (J1), defining Cloud Operations dashboards/SLO alert contracts (J2), and completing CI/CD migration/deploy safety gates (M1).

## Scope and Constraints
- In scope:
1. API + worker OTel bootstrap with trace/log correlation and OTLP exporter-ready configuration.
2. DB/client span coverage for asyncpg and httpx paths with stable service/resource metadata.
3. Initial J2 dashboard/alert IaC-like artifacts (repo-tracked JSON/YAML) and runbook wiring.
4. CI workflow safety gates for migration checks and controlled deploy sequencing.
- Out of scope:
1. Full production infra provisioning of Cloud Run/Vercel/Supabase credentials.
2. Non-critical custom metrics beyond J1/J2 launch signals.
3. End-to-end traffic replay/load testing (L2).
- Constraints:
1. Keep API/web/worker contracts stable while adding telemetry hooks.
2. Changes must stay reviewable and reversible by layer (API, workers, CI/docs).
3. Validate with existing lint/typecheck/test commands and report explicit gaps.

## Progress
- [x] Add shared OTel config module and dependency baseline (API/workers).
- [x] Instrument FastAPI request lifecycle + repository DB spans.
- [x] Instrument worker loop + JobClient HTTP spans + correlation context.
- [x] Add tests/contract checks for instrumentation plumbing where practical.
- [x] Add J2 dashboard/SLO alert config artifacts and runbook usage.
- [x] Complete M1 CI migration/deploy safety gates and document controls.
- [x] Run validation matrix and capture outcomes in agent docs.

## Decision Log
- 2026-02-11: Start from a fresh branch off latest `main` (`codex/j1-j2-m1-telemetry-safety`) to isolate observability/safety work from recent H2/L1 guardrail merges.
- 2026-02-11: Chose OTLP exporter-ready OTel bootstrap with env-controlled toggles and versioned Cloud Operations dashboard/alert artifacts to keep infra binding explicit and reversible.
- 2026-02-11: Added explicit CI `migration-safety` and `deploy-readiness-gate` jobs as M1 safety controls before introducing environment-specific deploy execution.

## Plan of Work
1. Telemetry foundation
- Deliverable: OTel dependency/config bootstrap with env-driven toggles and sane defaults.
- Paths: `api/pyproject.toml`, `workers/pyproject.toml`, `api/app/core/*`, `workers/app/core/*`.
2. API + worker instrumentation
- Deliverable: request/job lifecycle traces plus DB/http client spans and structured log correlation fields.
- Paths: `api/app/main.py`, `api/app/services/repository.py`, `workers/app/main.py`, `workers/app/services/job_client.py`.
3. J2 observability contracts
- Deliverable: dashboard + SLO alert definition artifacts plus operator docs.
- Paths: `docs/observability/**`, `.agent/RUNBOOK.md`.
4. M1 safety gates
- Deliverable: CI jobs/workflow controls for migration/deploy safety checks.
- Paths: `.github/workflows/*.yml`, `scripts/**`, `README.md`.

## Validation and Acceptance
1. `make lint`
- Expected: API/workers/web lint checks pass.
2. `make typecheck`
- Expected: API/workers/web type checks pass.
3. `make test`
- Expected: fast test suites pass.
4. `bash scripts/agent-hygiene-check.sh --mode project`
- Expected: agent workflow checks pass.
5. `git status --short`
- Expected: only intended telemetry/observability/safety changes.

## Idempotence and Recovery
1. Telemetry toggles are env-controlled; disabling OTel should preserve prior runtime behavior.
2. Dashboard/alert artifacts are declarative and versioned for deterministic re-apply.
3. CI safety jobs are additive and can be rolled back via workflow/file-level revert.

## Outcomes and Retrospective
- Outcome: `IN_PROGRESS`
- Follow-ups:
1. Validate telemetry payload quality against staging Cloud Operations once env creds/project IDs are available.
2. Expand alert tuning thresholds after first production traffic baseline.
