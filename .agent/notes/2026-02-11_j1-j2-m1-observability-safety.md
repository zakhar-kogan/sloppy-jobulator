# Task
- Request: Start a new branch from `main`, check implementation plan first, then execute J1 OTel instrumentation and progress J2 dashboards/SLO alerts + remaining M1 deploy/migration safety gates.
- Scope: API/workers telemetry bootstrap, CI safety workflow updates, observability docs/assets, and project-mode capture updates.
- Constraints: Keep diffs reviewable, preserve contracts, validate with repo commands.

## Actions Taken
1. Created branch `codex/j1-j2-m1-telemetry-safety` from updated `main` and opened active exec plan `EP-2026-02-11__j1-j2-m1-observability-safety`.
2. Added OTel dependency baselines (`api/pyproject.toml`, `workers/pyproject.toml`) and refreshed lockfiles (`api/uv.lock`, `workers/uv.lock`).
3. Added API telemetry bootstrap (`api/app/core/telemetry.py`) with FastAPI + asyncpg + httpx instrumentation, OTLP exporter config, and log-correlation record factory.
4. Added worker telemetry bootstrap (`workers/app/core/telemetry.py`) and instrumented worker lifecycle + JobClient operations (`workers/app/main.py`, `workers/app/services/job_client.py`).
5. Added J2 artifacts: dashboard JSON + alert policy YAML + import guidance (`docs/observability/**`), and linked runbook/readme guidance.
6. Added M1 safety controls: `scripts/migration-safety-gate.sh`, CI `migration-safety` job, and CI `deploy-readiness-gate` on `main`.
7. Updated roadmap/continuity/runbook/execplan capture to reflect J1/J2/M1 in-progress state.
8. Ran full DB integration + live E2E validation and hardened telemetry exporter bootstrap to avoid no-collector connection noise by requiring explicit OTLP endpoint configuration.

## What Went Wrong
1. Issue: `uv lock --project api` failed in sandbox due cache path permission.
- Root cause: sandbox denied access under `~/.cache/uv/sdists-v9`.
- Early signal missed: lock refresh requires writing to user-level uv cache.
- Prevention rule: when touching Python dependencies, immediately expect lock refresh and request escalation with an explicit `uv lock` prefix.
2. Issue: Initial typecheck command mixed API and worker packages and produced duplicate-module noise.
- Root cause: both services use top-level package name `app` and single mypy invocation crossed package roots.
- Early signal missed: monorepo package layout conflict appears only in combined invocation.
- Prevention rule: run mypy per service root (`api/app` and `workers/app` from `workers/` cwd).
3. Issue: Live E2E emitted repeated OTLP exporter connection errors when no local collector was running.
- Root cause: exporter was initialized without endpoint guards, resulting in localhost collector connection attempts.
- Early signal missed: initial test focus was functional pass/fail, not log noise quality.
- Prevention rule: keep instrumentation on by default, but only attach exporter when endpoint is explicitly set.

## What Went Right
1. Improvement: OTel baseline was added without changing API contracts.
- Evidence (time/readability/performance/manageability/modularity): focused new modules (`api/app/core/telemetry.py`, `workers/app/core/telemetry.py`) isolated setup concerns; existing route/service call signatures stayed unchanged.
- Why it worked: instrumentation integrated at runtime edges (FastAPI startup, worker loop, http/db client hooks) instead of invasive business-logic rewrites.
2. Improvement: Deploy/migration safety became explicit and machine-checked in CI.
- Evidence (time/readability/performance/manageability/modularity): dedicated `migration-safety` + `deploy-readiness-gate` jobs now enforce sequencing on `main`.
- Why it worked: introduced a small reusable gate script and clear workflow dependency graph.

## Reusable Learnings
1. Learning: OTel adoption in existing services should start with startup/shutdown bootstrap modules and edge instrumentation before adding custom domain metrics.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `PATTERNS.md`
- Why: repeatable for future services and minimizes regression risk.
2. Learning: Keep migration safety as a standalone CI job even when integration tests already apply schema.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `RUNBOOK.md`
- Why: preserves explicit migration control and clear operator visibility.

## Receipts
- Commands run:
  - `git pull --ff-only`
  - `git checkout -b codex/j1-j2-m1-telemetry-safety`
  - `(escalated) uv lock --project api`
  - `uv run --project api --extra dev ruff check api workers`
  - `uv run --project api --extra dev mypy api/app`
  - `(workdir workers) uv run --project ../api --extra dev mypy app`
  - `uv run --project api --extra dev pytest api/tests --ignore=api/tests/test_discovery_jobs_integration.py`
  - `uv run --project workers --extra dev pytest workers/tests`
  - `make db-up && make db-reset`
  - `SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py`
  - `UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... fnm exec --using 24.13.0 pnpm --dir web test:e2e:live`
  - `make db-down`
  - `bash scripts/agent-hygiene-check.sh --mode project`
- Files changed:
  - `.github/workflows/ci.yml`
  - `api/app/core/config.py`
  - `api/app/core/telemetry.py`
  - `api/app/main.py`
  - `api/pyproject.toml`
  - `api/uv.lock`
  - `workers/app/core/config.py`
  - `workers/app/core/telemetry.py`
  - `workers/app/main.py`
  - `workers/app/services/job_client.py`
  - `workers/pyproject.toml`
  - `workers/uv.lock`
  - `scripts/migration-safety-gate.sh`
  - `docs/observability/README.md`
  - `docs/observability/cloud-monitoring-dashboard.json`
  - `docs/observability/alert-policies.yaml`
  - `README.md`
  - `.agent/RUNBOOK.md`
  - `.agent/CONTINUITY.md`
  - `.agent/execplans/INDEX.md`
  - `.agent/execplans/active/EP-2026-02-11__j1-j2-m1-observability-safety.md`
  - `docs/roadmap/IMPLEMENTATION_PLAN_v1.2.md`
- Tests/checks:
  - `ruff`: pass
  - `mypy`: pass (API + workers scoped runs)
  - `pytest api/tests --ignore integration`: pass (`19/19`)
  - `pytest workers/tests`: pass (`6/6`)
  - `pytest api/tests/test_discovery_jobs_integration.py`: pass (`39/39`)
  - `pnpm --dir web test:e2e:live`: pass (`4/4`)
  - `agent-hygiene-check --mode project`: pass
