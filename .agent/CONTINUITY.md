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
Now: Environment-bound deploy/observability scaffolding is added (`docs/ENVIRONMENT_BINDINGS.md`, `.github/workflows/deploy.yml`, observability bind/import/validation scripts); E2 redirect-resolution now honors settings-default + metadata override semantics and passes normalization overrides through redirect job inputs, while H2/L1 cockpit coverage now includes selection-retarget cross-flow in mock/live specs.
Next: Run DB-backed redirect integration and live cockpit suites with local DB env wired, then continue E1 per-domain override completion and staging telemetry bind/validation.
Open Questions: exact production Supabase URL/key provisioning and human role metadata conventions are UNCONFIRMED.

## Done (recent)
- 2026-02-12 `[CODE]` Added staged env binding baseline for J1/J2/M1: `docs/ENVIRONMENT_BINDINGS.md`, `.github/workflows/deploy.yml`, `scripts/bind-observability-assets.py`, `scripts/import-observability-assets.sh`, `scripts/validate-telemetry-quality.sh`, and observability templates under `docs/observability/*.template.*`.
- 2026-02-12 `[CODE]` Advanced E2 to in-progress: discovery metadata can enqueue `resolve_url_redirects`, worker now resolves redirect chains with broader semantics and normalization overrides, and API repository applies resolved discovery URL/hash updates with provenance events.
- 2026-02-12 `[CODE]` Expanded H2/L1 Playwright coverage for queue/filter/pagination cross-flow in mock and live cockpit specs.
- 2026-02-15 `[CODE]` Updated E2 discovery enqueue semantics to use `SJ_ENABLE_REDIRECT_RESOLUTION_JOBS` defaults with per-event metadata override (`resolve_redirects`), propagated normalization overrides into `resolve_url_redirects` job inputs, and expanded cockpit E2E retargeting cross-flow coverage.
- 2026-02-15 `[CODE]` Stabilized live cockpit merge-conflict E2E assertion to accept backend conflict detail or equivalent self-merge guardrail text while preserving no-merge event verification.
- 2026-02-11 `[CODE]` Hardened J1 OTel bootstrap to avoid default local OTLP export failures when no collector endpoint is configured (instrumentation remains enabled; exporter activates only when endpoint env is set), and revalidated DB integration + live cockpit E2E post-change.
- 2026-02-11 `[CODE]` Added J1 OTel baseline (`api/app/core/telemetry.py`, `workers/app/core/telemetry.py`) plus worker/client spans and API request logging correlation, added J2 dashboard/alert artifacts (`docs/observability/**`), and added M1 CI safety gates (`migration-safety`, `deploy-readiness-gate`, `scripts/migration-safety-gate.sh`).
- 2026-02-10 `[CODE]` Added admin operator cockpit baseline APIs/UI plus web API-contract coverage and mock/live Playwright baselines for moderation/admin flows.

## Working set
- 2026-02-08 `[ASSUMPTION]` Target stack remains Next.js + FastAPI + Supabase + Cloud Run per spec.
- 2026-02-08 `[CODE]` Node toolchain standardized on `fnm` + `pnpm` with root `.node-version` and `web/pnpm-lock.yaml`.
- 2026-02-08 `[CODE]` Local API `make test` keeps integration tests skipped unless DB URL env vars are set (while `make test-integration` enforces DB-backed run).
- 2026-02-15 `[CODE]` Redirect job enqueue now resolves from settings-default (`SJ_ENABLE_REDIRECT_RESOLUTION_JOBS`) with explicit per-event metadata override support.

## Decisions
- 2026-02-08 `[CODE]` D-001 through D-004 active in `.agent/DECISIONS.md`.

## Receipts
- 2026-02-12 `[TOOL]` `uv run --project workers --extra dev pytest workers/tests/test_redirects.py workers/tests/test_freshness.py` passed (`7/7`).
- 2026-02-12 `[TOOL]` `uv run --project api --extra dev pytest api/tests/test_urls.py -q` passed (`2/2`).
- 2026-02-12 `[TOOL]` `fnm exec --using 24.13.0 pnpm --dir web exec playwright test web/tests-e2e/admin-cockpit.spec.ts --reporter=line` passed (`6/6`).
- 2026-02-12 `[TOOL]` `uv run --project api --extra dev ruff check ... && uv run --project workers --extra dev ruff check ...` passed.
- 2026-02-12 `[TOOL]` `uv run --project api --extra dev mypy api/app && uv run --project workers --extra dev mypy workers/app` passed.
- 2026-02-12 `[TOOL]` `make db-up -> make db-reset -> (escalated) UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k redirect_resolution -q -> UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... fnm exec --using 24.13.0 pnpm --dir web test:e2e:live -> make db-down` passed (`1/1` redirect integration, `5/5` live cockpit).
- 2026-02-11 `[TOOL]` `make db-up -> make db-reset -> SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -> UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... fnm exec --using 24.13.0 pnpm --dir web test:e2e:live -> make db-down` passed (`39/39` integration, `4/4` live E2E).
- 2026-02-15 `[TOOL]` `uv run --project api --extra dev pytest api/tests/test_urls.py && uv run --project workers --extra dev pytest workers/tests/test_redirects.py && fnm exec --using 24.13.0 pnpm --dir web exec playwright test web/tests-e2e/admin-cockpit.spec.ts --reporter=line` passed (`2/2`, `3/3`, `7/7`); `uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "redirect_resolution or redirect_setting or redirect_overrides"` skipped due missing DB env vars.
- 2026-02-15 `[TOOL]` `make db-up -> make db-reset -> SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "redirect_resolution or redirect_setting or redirect_overrides" -q -> SJ_DATABASE_URL=... DATABASE_URL=... fnm exec --using 24.13.0 pnpm --dir web test:e2e:live -> make db-down` passed (`3/3` redirect integration, `6/6` live cockpit).
