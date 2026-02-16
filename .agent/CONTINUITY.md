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
Now: E2/H2/public increments plus F2 trust-policy fallback hardening and L1 live cockpit rebaseline are validated; DB-backed trust/postings slices and full live cockpit suite are green.
Next: Execute staging/prod environment binding and validation for `J1/J2/M1`, then close residual `G1/H1` relevance and catalogue UX polish items.
Open Questions: exact production Supabase URL/key provisioning and human role metadata conventions are UNCONFIRMED.

## Done (recent)
- 2026-02-16 `[CODE]` Completed ordered product increment set with four commits: `013f8d2` (E2 cockpit redirect visibility), `53d8506` (H2 bulk/operator UX hardening), `7716ae3` (L1 live bulk moderation E2E), `acb8369` (public API-backed catalogue/search UX).
- 2026-02-16 `[CODE]` Closed trust-policy fallback and live cockpit rebaseline gaps: trusted/semi-trusted fallback defaults now enforce confidence-aware auto-publish behavior, and live cockpit E2E fixtures explicitly seed/select deterministic queue states.
- 2026-02-15 `[CODE]` Completed E1 persisted URL normalization overrides: added `url_normalization_overrides` DB table/trigger, admin CRUD+toggle API (`/admin/url-normalization-overrides`), repository validation/audit events, and shared persisted override hydration for ingest + redirect claim path.
- 2026-02-15 `[CODE]` Updated E2 discovery enqueue semantics to use `SJ_ENABLE_REDIRECT_RESOLUTION_JOBS` defaults with per-event metadata override (`resolve_redirects`), propagated normalization overrides into `resolve_url_redirects` job inputs, and expanded cockpit E2E retargeting cross-flow coverage.
- 2026-02-15 `[CODE]` Stabilized live cockpit merge-conflict E2E assertion to accept backend conflict detail or equivalent self-merge guardrail text while preserving no-merge event verification.
- 2026-02-11 `[CODE]` Hardened J1 OTel bootstrap to avoid default local OTLP export failures when no collector endpoint is configured (instrumentation remains enabled; exporter activates only when endpoint env is set), and revalidated DB integration + live cockpit E2E post-change.
- 2026-02-11 `[CODE]` Added J1 OTel baseline (`api/app/core/telemetry.py`, `workers/app/core/telemetry.py`) plus worker/client spans and API request logging correlation, added J2 dashboard/alert artifacts (`docs/observability/**`), and added M1 CI safety gates (`migration-safety`, `deploy-readiness-gate`, `scripts/migration-safety-gate.sh`).

## Working set
- 2026-02-08 `[ASSUMPTION]` Target stack remains Next.js + FastAPI + Supabase + Cloud Run per spec.
- 2026-02-08 `[CODE]` Node toolchain standardized on `fnm` + `pnpm` with root `.node-version` and `web/pnpm-lock.yaml`.
- 2026-02-08 `[CODE]` Local API `make test` keeps integration tests skipped unless DB URL env vars are set (while `make test-integration` enforces DB-backed run).
- 2026-02-15 `[CODE]` Redirect job enqueue now resolves from settings-default (`SJ_ENABLE_REDIRECT_RESOLUTION_JOBS`) with explicit per-event metadata override support.

## Decisions
- 2026-02-08 `[CODE]` D-001 through D-004 active in `.agent/DECISIONS.md`.

## Receipts
- 2026-02-16 `[TOOL]` `make db-up -> make db-reset -> (escalated) UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "redirect or admin_jobs" -> make db-down` passed (`6/6` selected DB-backed API tests).
- 2026-02-16 `[TOOL]` `SJ_DATABASE_URL=... DATABASE_URL=... fnm exec --using 24.13.0 pnpm --dir web test:e2e:live` failed (`3/8` pass): failures are in pre-existing live cockpit scenarios that assume `needs_review` candidates on filtered pages and old patch-option expectations (`closed` absent).
- 2026-02-16 `[TOOL]` `make db-up -> make db-reset -> (escalated) SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k trust_policy -> (escalated) ... -k postings -> (escalated) fnm exec --using 24.13.0 pnpm --dir web exec playwright test -c playwright.live.config.ts web/tests-e2e/admin-cockpit.live.spec.ts --reporter=line` passed (`16/16` trust-policy slice, `4/4` postings slice, `8/8` live cockpit).
- 2026-02-16 `[TOOL]` `GCP_PROJECT_ID=sloppy-jobulator SJ_OBS_ENVIRONMENT=staging SJ_OBS_API_CLOUD_RUN_SERVICE=sloppy-jobulator-api-staging SJ_OBS_WORKER_OTEL_SERVICE=sloppy-jobulator-workers-staging SJ_API_BASE_URL=https://sloppy-jobulator-api-staging-uylwyqgtza-uc.a.run.app bash scripts/validate-telemetry-quality.sh` failed cleanly after script hardening: API probe falls back to `/`, API request_count series resolves, worker backlog series is missing for configured staging labels.
- 2026-02-16 `[TOOL]` `GCP_PROJECT_ID=sloppy-jobulator SJ_OBS_ENVIRONMENT=staging ... SJ_OBS_SKIP_ALERT_POLICIES=true bash scripts/import-observability-assets.sh` now performs idempotent dashboard import (create then update path verified), duplicate dashboard created during script iteration was removed, and alert-policy import is explicitly skipped when `gcloud alpha` is not installed.
- 2026-02-12 `[TOOL]` `uv run --project workers --extra dev pytest workers/tests/test_redirects.py workers/tests/test_freshness.py` passed (`7/7`).
- 2026-02-12 `[TOOL]` `uv run --project api --extra dev pytest api/tests/test_urls.py -q` passed (`2/2`).
- 2026-02-12 `[TOOL]` `fnm exec --using 24.13.0 pnpm --dir web exec playwright test web/tests-e2e/admin-cockpit.spec.ts --reporter=line` passed (`6/6`).
- 2026-02-12 `[TOOL]` `uv run --project api --extra dev ruff check ... && uv run --project workers --extra dev ruff check ...` passed.
- 2026-02-12 `[TOOL]` `uv run --project api --extra dev mypy api/app && uv run --project workers --extra dev mypy workers/app` passed.
- 2026-02-12 `[TOOL]` `make db-up -> make db-reset -> (escalated) UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k redirect_resolution -q -> UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... fnm exec --using 24.13.0 pnpm --dir web test:e2e:live -> make db-down` passed (`1/1` redirect integration, `5/5` live cockpit).
- 2026-02-11 `[TOOL]` `make db-up -> make db-reset -> SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -> UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... fnm exec --using 24.13.0 pnpm --dir web test:e2e:live -> make db-down` passed (`39/39` integration, `4/4` live E2E).
- 2026-02-15 `[TOOL]` `uv run --project api --extra dev pytest api/tests/test_urls.py && uv run --project workers --extra dev pytest workers/tests/test_redirects.py && fnm exec --using 24.13.0 pnpm --dir web exec playwright test web/tests-e2e/admin-cockpit.spec.ts --reporter=line` passed (`2/2`, `3/3`, `7/7`); `uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "redirect_resolution or redirect_setting or redirect_overrides"` skipped due missing DB env vars.
- 2026-02-15 `[TOOL]` `make db-up -> make db-reset -> SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "redirect_resolution or redirect_setting or redirect_overrides" -q -> SJ_DATABASE_URL=... DATABASE_URL=... fnm exec --using 24.13.0 pnpm --dir web test:e2e:live -> make db-down` passed (`3/3` redirect integration, `6/6` live cockpit).
- 2026-02-15 `[TOOL]` `make db-up -> make db-reset -> (escalated) UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "redirect_resolution or url_normalization_override" -q -> (escalated) SJ_DATABASE_URL=... DATABASE_URL=... fnm exec --using 24.13.0 pnpm --dir web test:e2e:live --grep "admin override mutation changes discovery normalization for seeded URL" -> make db-down` passed (`6/6` targeted integration, `1/1` new live admin E2E).
