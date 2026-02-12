# Continuity Ledger

Facts only. No transcripts. If unknown, write `UNCONFIRMED`.
Each entry must include date and provenance tag: `[USER]`, `[CODE]`, `[TOOL]`, `[ASSUMPTION]`.
In `project` mode, update this file whenever Goal/Now/Next/Decisions materially change.
In `template` mode, keep this file as scaffold-only.

## Size caps
- Snapshot: <= 25 non-empty lines.
- Done (recent): <= 7 bullets.
- Working set: <= 12 bullets.
- Receipts: <= 20 bullets (keep recent, compress older items).

## Snapshot

Goal: Ship Phase 1 baseline with DB-backed API/worker runtime, observability baseline, and deploy/migration safety gates.
Now: `codex/phase2-p0-env-h2-l1-e2` adds remaining environment-binding scaffolding and phase-followup execution: deploy workflow (`.github/workflows/deploy.yml`) is wired behind successful `CI` runs on `main` (or manual dispatch), observability environment binding guidance is versioned (`docs/observability/ENVIRONMENT_BINDINGS.md`), cockpit maintenance actions require explicit confirmation (`CONFIRM`) with matching mocked/live Playwright coverage, and E2 v0 redirect-resolution path is started (flag-gated enqueue + worker resolver + API result-apply canonical update/replay enqueue).
Next: Bind real staging/production secrets/channels for deploy and observability imports, run first staging deploy/telemetry validation, and continue E2 semantics beyond v0 (domain overrides + broader redirect behaviors).
Open Questions: exact production Supabase URL/key provisioning and human role metadata conventions are UNCONFIRMED.

## Done (recent)
- 2026-02-12 `[CODE]` Added M1 deploy execution workflow (`.github/workflows/deploy.yml`) with main-branch CI-success gating and manual environment dispatch, plus secret-bound skip-safe behavior.
- 2026-02-12 `[CODE]` Added J1/J2 environment-binding guidance (`docs/observability/ENVIRONMENT_BINDINGS.md`) and linked runbook/readme updates.
- 2026-02-12 `[CODE]` Added H2 cockpit maintenance confirmation guardrail (`CONFIRM`) and expanded L1 mocked/live Playwright coverage for disabled/enabled maintenance action states.
- 2026-02-12 `[CODE]` Started E2 redirect-resolution async path: feature-flagged enqueue (`SJ_ENABLE_REDIRECT_RESOLUTION_JOBS`), worker resolver job execution, and API job-result apply updating discovery canonical fields with extract replay enqueue when changed.
- 2026-02-11 `[CODE]` Hardened J1 OTel bootstrap to avoid default local OTLP export failures when no collector endpoint is configured (instrumentation remains enabled; exporter activates only when endpoint env is set), and revalidated DB integration + live cockpit E2E post-change.
- 2026-02-11 `[CODE]` Added J1 OTel baseline (`api/app/core/telemetry.py`, `workers/app/core/telemetry.py`) plus worker/client spans and API request logging correlation, added J2 dashboard/alert artifacts (`docs/observability/**`), and added M1 CI safety gates (`migration-safety`, `deploy-readiness-gate`, `scripts/migration-safety-gate.sh`).

## Working set
- 2026-02-08 `[ASSUMPTION]` Target stack remains Next.js + FastAPI + Supabase + Cloud Run per spec.
- 2026-02-08 `[CODE]` Node toolchain standardized on `fnm` + `pnpm` with root `.node-version` and `web/pnpm-lock.yaml`.
- 2026-02-08 `[CODE]` Local API `make test` keeps integration tests skipped unless DB URL env vars are set (while `make test-integration` enforces DB-backed run).

## Decisions
- 2026-02-08 `[CODE]` D-001 through D-004 active in `.agent/DECISIONS.md`.

## Receipts
- 2026-02-12 `[TOOL]` `uv run --project workers --extra dev pytest workers/tests` passed (`9/9`) including new redirect-resolution unit coverage.
- 2026-02-12 `[TOOL]` `(escalated) source .venv/bin/activate && SJ_DATABASE_URL=... DATABASE_URL=... pytest tests/test_discovery_jobs_integration.py -k "redirect_resolution_job_enqueued_when_flag_enabled or resolve_redirect_job_result_updates_discovery_and_enqueues_extract"` passed (`2/2` selected).
- 2026-02-12 `[TOOL]` `fnm exec --using 24.13.0 pnpm --dir web typecheck -> fnm exec --using 24.13.0 pnpm --dir web test:e2e` passed (`5/5` mocked cockpit specs).
- 2026-02-12 `[TOOL]` `source .venv/bin/activate && ruff check ...` passed for touched API and worker files.
- 2026-02-12 `[TOOL]` `make db-up -> make db-reset -> make db-down` passed for local integration lifecycle during E2 verification.
- 2026-02-11 `[TOOL]` `make db-up -> make db-reset -> SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -> UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... fnm exec --using 24.13.0 pnpm --dir web test:e2e:live -> make db-down` passed (`39/39` integration, `4/4` live E2E).
- 2026-02-11 `[TOOL]` `(escalated) uv lock --project api` refreshed `api/uv.lock` for OTel deps.
- 2026-02-11 `[TOOL]` `uv run --project api --extra dev ruff check api workers -> mypy api/app -> (workdir workers) uv run --project ../api --extra dev mypy app -> pytest api/tests --ignore=api/tests/test_discovery_jobs_integration.py -> uv run --project workers --extra dev pytest workers/tests -> bash scripts/agent-hygiene-check.sh --mode project` passed.
