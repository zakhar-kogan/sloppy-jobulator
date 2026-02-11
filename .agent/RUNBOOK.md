# Runbook

## Setup and local run
1. Install dependencies:
- API: `cd api && python -m venv .venv && source .venv/bin/activate && pip install -e .[dev]`
- Workers: `cd workers && python -m venv .venv && source .venv/bin/activate && pip install -e .[dev]`
- Web: `fnm use 24.13.0 && pnpm install --dir web`
2. Start local services:
- API: `cd api && uvicorn app.main:app --reload`
- Worker: `cd workers && python -m app.main`
- Web (public shell): `fnm use 24.13.0 && pnpm --dir web dev`
- Web (admin trust-policy console enabled): `SJ_API_URL=http://localhost:8000 SJ_ADMIN_BEARER=<admin-jwt> fnm use 24.13.0 && pnpm --dir web dev`
3. Run app locally: start API + web for browsing, then worker for job processing.

## Build/test/quality
1. Build: `python -m compileall api/app workers/app` and `fnm exec --using 24.13.0 pnpm --dir web build`
2. Test: `cd api && pytest` and `cd workers && pytest`
3. Lint: `cd api && ruff check app tests` and `cd workers && ruff check app tests` and `fnm exec --using 24.13.0 pnpm --dir web lint`
4. Typecheck: `cd api && mypy app` and `cd workers && mypy app` and `fnm exec --using 24.13.0 pnpm --dir web typecheck`
5. Required pre-finalization checks (fill with concrete commands): `bash scripts/agent-hygiene-check.sh --mode project`
6. CI gate split (`M1 + L1`):
- Fast lane: `api-fast`, `workers`, `web`.
- DB-backed integration lane: `api-integration-db` (runs `api/tests/test_discovery_jobs_integration.py` with Postgres + schema apply).
- Branch protection should require: `api-fast`, `api-integration-db`, `workers`, `web`, and `validate-agent-contract`.
7. Live browser E2E reliability baseline:
- Install cached browser runtime explicitly before live runs: `fnm exec --using 24.13.0 pnpm --dir web exec playwright install chromium`.
- Keep live Playwright retries disabled (`web/playwright.live.config.ts` uses `retries: 0`); apply retry-once only at CI step level for transient startup failures.
- Use explicit timeout budgets for live job setup/run steps and cache `uv`, `pnpm`, and Playwright browser artifacts in CI.

## Database operations
1. Migration command: `DATABASE_URL=... bash scripts/apply_db_schema.sh`
2. Seed command: included in `scripts/apply_db_schema.sh` (`db/seeds/001_taxonomy.sql`)
3. Rollback/recovery: `UNCONFIRMED` (down migrations not implemented yet)
4. Local integration DB lifecycle:
- Start DB: `make db-up`
- Reset schema+seed: `make db-reset`
- Run API integration tests: `make test-integration`
- Stop DB: `make db-down`
5. Before running compose targets, verify Docker daemon availability (`docker info` or equivalent) to avoid socket connection failures.

## Supabase human role provisioning (B3)
1. Bootstrap SQL command:
- `python scripts/bootstrap_admin.py --user-id <supabase-user-uuid> --role admin`
- Alternative target by email: `python scripts/bootstrap_admin.py --email <user@example.org> --role moderator`
2. The script emits SQL for `auth.users.raw_app_meta_data.role` plus a provenance event insert.
3. Source of truth for elevated roles is Supabase `app_metadata` only; `user_metadata` must not grant `moderator`/`admin`.
4. API claim resolution order is:
- `app_metadata.role`
- `app_metadata.sj_role`
- first recognized value in `app_metadata.roles[]`
5. Allowed role values: `user`, `moderator`, `admin` (unknown values downgrade to `user`).
6. Example SQL (run in Supabase SQL editor with admin privileges):
- Set moderator role:
```sql
update auth.users
set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) || jsonb_build_object('role', 'moderator')
where id = '00000000-0000-0000-0000-000000000000'::uuid;
```
- Set admin role:
```sql
update auth.users
set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) || jsonb_build_object('role', 'admin')
where id = '00000000-0000-0000-0000-000000000000'::uuid;
```
7. Verification query:
```sql
select id, raw_app_meta_data
from auth.users
where id = '00000000-0000-0000-0000-000000000000'::uuid;
```
8. After claim updates, refresh/re-authenticate the session so new JWT claims propagate to API calls.

## Trust-policy publish routing (F2 baseline)
1. Extract projection resolves policy from `source_trust_policy` in precedence order:
- explicit `source_key`
- `module:<module_id>`
- `default:<module_trust_level>`
2. Publish routing currently maps to:
- auto-publish path: candidate `published`, posting `active`
- moderation path: candidate `needs_review`, posting `archived`
3. Merge-aware routing keys (inside `source_trust_policy.rules_json`) are:
- `merge_decision_actions`: maps dedupe decisions to candidate action (`needs_review`, `reject`, `archive`, `preserve`).
- `merge_decision_reasons`: overrides policy `reason` receipt per merge decision.
- `moderation_routes`: assigns queue route labels for `needs_review`/`rejected` decisions.
- `default_moderation_route`: fallback route label when no per-decision route is set.
4. `auto_merge_blocked` handling:
- machine auto-merge fallback writes merge decision `needs_review` plus `merge_metadata.auto_merge_blocked=true`.
- policy routing keys do not branch directly on metadata; route this path via `needs_review` overrides and inspect metadata in provenance for audits.
5. Example: force rejected state when auto-merge fallback occurs for a sensitive source:
```sql
insert into source_trust_policy (
  source_key,
  trust_level,
  auto_publish,
  requires_moderation,
  rules_json,
  enabled
)
values (
  'source:high-risk-feed',
  'trusted',
  true,
  false,
  jsonb_build_object(
    'min_confidence', 0.0,
    'merge_decision_actions', jsonb_build_object('needs_review', 'reject'),
    'merge_decision_reasons', jsonb_build_object('needs_review', 'policy_auto_merge_blocked_requires_reject'),
    'moderation_routes', jsonb_build_object('needs_review', 'dedupe.auto_merge_conflict_queue')
  ),
  true
)
on conflict (source_key) do update set
  trust_level = excluded.trust_level,
  auto_publish = excluded.auto_publish,
  requires_moderation = excluded.requires_moderation,
  rules_json = excluded.rules_json,
  enabled = true;
```
6. Example: keep fallback in moderation queue (no auto-reject), but route to dedicated triage:
```sql
insert into source_trust_policy (
  source_key,
  trust_level,
  auto_publish,
  requires_moderation,
  rules_json,
  enabled
)
values (
  'source:manual-triage-feed',
  'trusted',
  true,
  false,
  jsonb_build_object(
    'min_confidence', 0.0,
    'merge_decision_actions', jsonb_build_object('needs_review', 'needs_review'),
    'merge_decision_reasons', jsonb_build_object('needs_review', 'policy_manual_triage_required'),
    'moderation_routes', jsonb_build_object('needs_review', 'dedupe.manual_triage')
  ),
  true
)
on conflict (source_key) do update set
  trust_level = excluded.trust_level,
  auto_publish = excluded.auto_publish,
  requires_moderation = excluded.requires_moderation,
  rules_json = excluded.rules_json,
  enabled = true;
```
7. Verification query (latest policy receipt for candidate):
```sql
select
  payload->>'reason' as reason,
  payload->>'moderation_route' as moderation_route,
  payload->>'merge_decision' as merge_decision,
  payload->'merge_metadata'->>'auto_merge_blocked' as auto_merge_blocked
from provenance_events
where entity_type = 'posting_candidate'
  and entity_id = '00000000-0000-0000-0000-000000000000'::uuid
  and event_type = 'trust_policy_applied'
order by id desc
limit 1;
```
8. Every policy decision emits `provenance_events` with `event_type='trust_policy_applied'`; use this first when debugging unexpected publish/moderation outcomes.
9. Admin API policy-management flow (preferred over direct SQL for day-to-day ops):
- Required auth: bearer token for a human principal with `admin:write` scope (Supabase `app_metadata.role = admin`).
- Suggested env vars:
```bash
export SJ_API_URL="http://localhost:8000"
export SJ_ADMIN_BEARER="<admin-jwt>"
```
- List policies:
```bash
curl -sS \
  -H "Authorization: Bearer ${SJ_ADMIN_BEARER}" \
  "${SJ_API_URL}/admin/source-trust-policy?limit=50&offset=0"
```
- Upsert one policy:
```bash
curl -sS -X PUT \
  -H "Authorization: Bearer ${SJ_ADMIN_BEARER}" \
  -H "Content-Type: application/json" \
  "${SJ_API_URL}/admin/source-trust-policy/source:high-risk-feed" \
  -d '{
    "trust_level": "trusted",
    "auto_publish": true,
    "requires_moderation": false,
    "enabled": true,
    "rules_json": {
      "min_confidence": 0.0,
      "merge_decision_actions": {"needs_review": "reject"},
      "merge_decision_reasons": {"needs_review": "policy_auto_merge_blocked_requires_reject"},
      "moderation_routes": {"needs_review": "dedupe.auto_merge_conflict_queue"}
    }
  }'
```
- Toggle enablement:
```bash
curl -sS -X PATCH \
  -H "Authorization: Bearer ${SJ_ADMIN_BEARER}" \
  -H "Content-Type: application/json" \
  "${SJ_API_URL}/admin/source-trust-policy/source:high-risk-feed" \
  -d '{"enabled": false}'
```
10. Validation contract for admin writes:
- Invalid merge-routing payloads return HTTP `422` with repository validation detail (for example invalid action, invalid route label, unknown merge-decision key).
11. Audit verification query for admin policy writes/toggles:
```sql
select
  pe.event_type,
  pe.actor_id::text as actor_user_id,
  pe.payload->>'source_key' as source_key,
  pe.payload->>'operation' as operation,
  pe.payload->>'previous_enabled' as previous_enabled,
  pe.payload->>'enabled' as enabled,
  pe.created_at
from provenance_events pe
join source_trust_policy stp on stp.id = pe.entity_id
where pe.entity_type = 'source_trust_policy'
  and stp.source_key = 'source:high-risk-feed'
  and pe.event_type in ('policy_upserted', 'policy_enabled_changed')
order by pe.id desc
limit 20;
```
12. Event semantics:
- `policy_upserted`: emitted on admin `PUT`; payload includes `operation` (`created|updated`) plus current policy fields.
- `policy_enabled_changed`: emitted on admin `PATCH`; payload includes `previous_enabled` and new `enabled` value.
13. Web admin console path:
- URL: `/admin/source-trust-policy` in the Next.js app.
- The page calls Next.js proxy routes (`/api/admin/source-trust-policy` and `/api/admin/source-trust-policy/{sourceKey}`), which require `SJ_API_URL` and `SJ_ADMIN_BEARER` env vars on the web server process.
14. Operator cockpit API endpoints:
- Candidate queue/actions: `GET /candidates`, `PATCH /candidates/{candidateId}`, `POST /candidates/{candidateId}/merge`, `POST /candidates/{candidateId}/override` (requires `moderation:read|write`; admin tokens include these scopes).
- Modules visibility/mutation: `GET /admin/modules`, `PATCH /admin/modules/{moduleId}` (supports safe `enabled` toggle).
- Jobs visibility/maintenance: `GET /admin/jobs`, `POST /admin/jobs/reap-expired`, `POST /admin/jobs/enqueue-freshness` (bounded by `limit` query param).
15. Operator cockpit web path:
- URL: `/admin/cockpit` in the Next.js app.
- Server proxy routes: `/api/admin/candidates/**`, `/api/admin/modules/**`, `/api/admin/jobs/**` forwarding to API with `SJ_ADMIN_BEARER`.

## Incident basics
1. Health check endpoint/command: `GET /healthz` on API.
2. Log query path: `UNCONFIRMED` (Cloud Logging filters pending infra setup).
3. Rollback command/path: `UNCONFIRMED` (deployment automation pending).

## Agentic framework maintenance
1. Set workflow mode explicitly:
- Template repo: `--mode template` (sanitized scaffold only).
- Downstream project repo: `--mode project` (full task-state capture).
2. For substantial tasks, run a balanced review:
- What went wrong, why, prevention?
- What went right, measurable improvement, reusable or not?
3. Triage each item as `promote now | pilot backlog | keep local`.
4. In `project` mode, update notes/helpers/continuity and promote high-leverage items.
5. In `template` mode, do not record live task state; only improve reusable template policy/docs/scripts.
6. Weekly hygiene: prune stale notes, deduplicate conflicting guidance, and update `UNCONFIRMED` commands when known.
7. Run contract checks: `bash scripts/agent-hygiene-check.sh --mode template|project`.
8. Run weekly maintenance review: `bash scripts/agent-weekly-review.sh --mode template|project`.
9. Keep spec/roadmap references pointed at `docs/spec/` and `docs/roadmap/`; avoid relying on external handoff folders.
10. After doc migrations/imports, run a quick absolute-path scan before hygiene/CI (for example, check for machine-local home-directory prefixes).
