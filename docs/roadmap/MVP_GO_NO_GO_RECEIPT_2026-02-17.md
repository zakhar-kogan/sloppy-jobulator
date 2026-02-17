# MVP GO/NO-GO Receipt

Date: `2026-02-17`  
Commit baseline: `fe85329` (plus local fix pending commit)  
Environment: `staging` + local DB-backed test environment

## Verdict

`NO-GO`

Reason: staging API cannot serve postings (`/postings?limit=1`) due missing `SJ_DATABASE_URL` binding.

## Gate Results

### Gate 1: Core stack healthy

- Staging API root: `GET /` -> `200` (`{"status":"ok"}`) ✅
- Staging API health endpoint: `GET /healthz` -> `404` ⚠️ (route mismatch on staging endpoint path)
- Staging postings: `GET /postings?limit=1` -> `503` with `{"detail":"SJ_DATABASE_URL is required"}` ❌

Status: `FAILED`

### Gate 2: End-to-end ingestion to public visibility

Local DB-backed evidence:

- `pytest -k "enqueue_claim_result_and_projection_flow or admin_jobs_visibility_and_safe_mutations"` -> `2 passed` ✅

Status: `PASSED` (local)

### Gate 3: Admin control plane minimal + working

Local DB-backed evidence:

- `pytest -k "admin_modules or admin_jobs_requires_admin_scope"` -> `3 passed` ✅
- `pytest -k "admin_connector_modules_include_ingestion_health"` -> `1 passed` ✅

Status: `PASSED` (local)

### Gate 4: Public UX MVP contract

- `pnpm --dir web run typecheck` -> pass ✅

Status: `PASSED`

## Commands Run

```bash
make db-up
make db-reset
UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sloppy_jobulator DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sloppy_jobulator uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "enqueue_claim_result_and_projection_flow or admin_jobs_visibility_and_safe_mutations" -q
UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sloppy_jobulator DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sloppy_jobulator uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "admin_modules or admin_jobs_requires_admin_scope" -q
UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sloppy_jobulator DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sloppy_jobulator uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "admin_connector_modules_include_ingestion_health" -q
fnm exec --using 24.13.0 pnpm --dir web run typecheck
curl -sS https://sloppy-jobulator-api-staging-uylwyqgtza-uc.a.run.app/
curl -sS https://sloppy-jobulator-api-staging-uylwyqgtza-uc.a.run.app/healthz
curl -sS "https://sloppy-jobulator-api-staging-uylwyqgtza-uc.a.run.app/postings?limit=1"
make db-down
```

## Blocking Issues

1. Staging API missing DB binding (`SJ_DATABASE_URL`) causing `503` for postings endpoints.
2. Staging health route check expects `/healthz`, but staging returned `404`; verify deployed router prefix and health path.

## Immediate Cutover Actions

1. Fix staging secret/env bindings for API service (`SJ_DATABASE_URL` and any dependent DB envs).
2. Redeploy API staging revision.
3. Re-run Gate 1 staging checks (`/`, `/healthz`, `/postings?limit=1`).
4. If all green, rerun full checklist and produce final GO receipt.
