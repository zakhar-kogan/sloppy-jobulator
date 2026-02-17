# MVP Ship Gate + Cutover Checklist

Date baseline: `2026-02-17`

Purpose: define a strict go/no-go gate for MVP launch without adding new scope.

## Gate 1: Core stack is healthy

1. API health endpoint returns 200.
2. Web app loads and renders public catalogue.
3. Database is reachable and seeded modules exist (`local-connector`, `local-processor`).

Suggested checks:

```bash
curl -sS http://127.0.0.1:8000/healthz
curl -sS "http://127.0.0.1:8000/postings?limit=1"
```

## Gate 2: End-to-end ingestion to public visibility

1. Connector can submit a discovery with URL.
2. Extract job is created and processed to `done`.
3. Candidate appears in admin queue.
4. Candidate can be patched/overridden to publishable/published state.
5. Posting appears on:
   - public list `/`
   - detail page `/postings/[id]`

Suggested checks:

```bash
make db-up
make db-reset
UV_CACHE_DIR=/tmp/uv-cache \
SJ_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sloppy_jobulator \
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sloppy_jobulator \
uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py \
  -k "enqueue_claim_result_and_projection_flow or admin_jobs_visibility_and_safe_mutations" -q
make db-down
```

## Gate 3: Admin control plane is minimal + working

1. Admin cockpit lists queue/modules/jobs.
2. Connector module rows show ingestion health:
   - `ingested_count`
   - `last_ingested_at`
   - `last_ingest_error_at`
   - `last_ingest_error`
3. Non-admin tokens are rejected for `/admin/*`.

Suggested checks:

```bash
UV_CACHE_DIR=/tmp/uv-cache \
SJ_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sloppy_jobulator \
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sloppy_jobulator \
uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py \
  -k "admin_modules or admin_jobs_requires_admin_scope" -q
```

## Gate 4: Public UX MVP contract

1. List page supports filtering/search and links to dedicated detail pages.
2. Detail page is shareable/canonical (`/postings/[id]`) and has:
   - source link
   - optional apply link
   - simple related navigation (same org / top tag).

Suggested checks:

```bash
fnm exec --using 24.13.0 pnpm --dir web run typecheck
```

## Cutover steps (launch mode)

1. Freeze scope to MVP-only surfaces:
   - public catalogue + detail
   - admin cockpit queue/management
   - ingestion connectors
   - auth separation.
2. Keep optional/non-core admin pages unlinked from primary navigation.
3. Run all gate checks above in staging.
4. If all gates pass, deploy API/workers/web.
5. Record one launch receipt with:
   - commit SHA
   - environment
   - command outputs (pass/fail summary)
   - known residual risks.

## Go/No-Go rule

- `GO`: all gates green, no P0/P1 regression in ingestion/moderation/public visibility.
- `NO-GO`: any gate red; rollback to prior green commit and reopen only failing slice.
