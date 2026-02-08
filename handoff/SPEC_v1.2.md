# Spec v1.2: Public Research Opportunities Aggregator

## 0) Purpose
Aggregate opportunities from external modules and user submissions, dedupe and extract structured fields, then publish a public searchable catalogue with strong freshness and provenance.

## 1) Scope

### 1.1 In scope (v1)
1. Public catalogue (no login required to browse).
2. External modules:
- Connectors submit discoveries and evidence.
- Processors claim jobs and submit extraction/dedupe/enrichment results.
3. Authenticated users can submit postings (moderated).
4. Admin/moderator controls for modules, merges, overrides, publishing.
5. Daily freshness checks and archive lifecycle.
6. Full event/provenance trail for ingestion, checks, merges, moderation.

### 1.2 Out of scope (v1)
1. Notifications.
2. Application tracking.
3. Sharing/collaboration features.
4. Heavy browser automation as core requirement (allowed as connector-specific extension).

## 2) Roles and identities
1. `visitor`: public read-only.
2. `user`: authenticated, can submit opportunities to moderation.
3. `moderator`: review approve/reject/merge/archive.
4. `admin`: manage modules, policies, taxonomy, and roles.
5. `bot`: machine identity for connectors/processors with scoped permissions.

## 3) System architecture
1. Frontend: Next.js (public catalogue + admin/moderation UI), deployed on Vercel.
2. Backend/control plane: FastAPI on Cloud Run.
3. Data/auth: Supabase Postgres + Supabase Auth + RLS.
4. Workers: Python Cloud Run Jobs.
5. Evidence storage: provider-agnostic blob/object store.
6. Queue/execution: Postgres durable job ledger first, with abstraction for future Temporal/Prefect/Windmill.

## 4) Module registry (external-first)
1. Module kinds: `connector`, `processor`.
2. Connector intake modes: `api`, `rss`, `scrape`, `webhook`, `telegram`, `manual`.
3. Module fields:
- `module_id`, `name`, `kind`, `enabled`
- `scopes[]`
- `config_schema`, `default_config`
- `trust_level` (`trusted`, `semi_trusted`, `untrusted`)
- timestamps
4. Credentials:
- per-module key/JWT, rotatable and revocable.
- scope enforcement on every request.

## 5) Data model (core entities)
1. `Module`
2. `Discovery` (append-only raw intake)
3. `Evidence` (blob pointer + metadata)
4. `PostingCandidate` (dedupe bucket + processing state)
5. `Posting` (public canonical record)
6. `Job` (durable work ledger)
7. `provenance_events` (checks/merge/moderation/publish/status changes)
8. `candidate_merge_decisions`
9. `submission_queue`
10. `source_trust_policy`

## 6) Key invariants
1. Discoveries are append-only and never hard-deleted.
2. Evidence is stored by pointer; DB stores metadata and references.
3. Dedupe/merge happens at `PostingCandidate`.
4. `Posting` is canonical public projection of reviewed/publishable candidate.
5. Every state mutation emits provenance event.
6. URL normalization always writes `normalized_url` and `canonical_hash`.

## 7) Lifecycle and publishing policy
1. Candidate states: `discovered`, `processed`, `publishable`, `published`, `rejected`, `closed`, `archived`, `needs_review`.
2. Publish policy:
- trusted connectors: auto-publish if checks and dedupe confidence pass.
- semi-trusted: auto-publish unless risk/conflict flags.
- untrusted and user submissions: moderation required.
3. Freshness:
- re-check active postings every 24h.
- retry transient failures before downgrading status.
- stale/closed postings archived from default public listing (history retained).

## 8) Contracts

### 8.1 DiscoveryEvent (connector -> API)
1. Fields:
- `origin_module_id`
- `external_id` (recommended)
- `discovered_at`
- `url` (optional)
- `title_hint` (optional)
- `text_hint` (optional)
- `evidence_refs[]` (optional)
- `metadata` (json)
2. Idempotency:
- unique `(origin_module_id, external_id)` when present.
- fallback unique `(origin_module_id, normalized_url)`.

### 8.2 Evidence
1. Fields:
- `evidence_id`
- `kind` (`url_fetch`, `html_snapshot`, `screenshot`, `text`, `rss_item`, `social_post`, `telegram_message`, `other`)
- `uri`
- `content_hash`
- `captured_at`
- optional `content_type`, `byte_size`
2. Policy:
- always keep minimal evidence (url + metadata + capped text).
- keep heavy artifacts when provided or policy-enabled.

### 8.3 Posting (canonical)
1. Required:
- `id`, `title`, `canonical_url`, `normalized_url`, `canonical_hash`
- `sector`, `degree_level`, `opportunity_kind`
- `organization_name`
- `country` or `remote=true`
- `source_refs[]`
2. Recommended:
- `tags[]`, `areas[]`, `description_text`, `application_url`, `deadline`
3. Optional:
- `city`, `region`, `department`, `lab_group`, `contact_people[]`, `language`
4. Provenance:
- per-field source/evidence/confidence (phased rollout).

## 9) Dedupe and merge
1. Strong signals:
- canonical/normalized URL equality
- application URL equality
- canonical hash equality
2. Medium signals:
- weighted text similarity (title + organization + key phrases).
3. Tie-breakers:
- NER overlap (org/location/person)
- contact email/domain collisions.
4. Merge policy:
- auto-merge only high-confidence matches (precision-first).
- uncertain/conflicting matches -> moderation queue.
- retain all discoveries/evidence links after merge.

### 9.1 URL normalization and redirect policy
1. Normalize conservatively and deterministically:
- lowercase scheme and host
- remove default ports
- trim trailing slash where safe
- strip known tracking params (`utm_*`, `ref`, configured list)
- sort query params by key for stable canonicalization
2. Do not blindly lowercase full paths or query values; some sources are case-sensitive.
3. Keep per-domain normalization overrides in config.
4. Redirect resolution must be asynchronous. It runs via background job and never blocks ingestion.

## 10) Jobs (durable ledger)
1. Job kinds: `dedupe`, `extract`, `enrich`, `check_freshness`, `resolve_url_redirects`.
2. Job fields:
- `job_id`, `kind`, `target_type`, `target_id`
- `inputs_json`
- `status` (`queued`, `claimed`, `done`, `failed`, `dead_letter`)
- `attempt`
- `locked_by_module_id`, `locked_at`, `lease_expires_at`
- `result_json`, `error_json`
- timestamps
3. Execution model:
- processor polls eligible jobs.
- claim with lease.
- submit result patch.
4. Required safeguards:
- lease reaper resets expired claimed jobs to queued.
- exponential backoff with jitter for worker polling and retries.

## 11) APIs

### 11.1 Public
1. `GET /postings` (filter/sort/search/pagination)
2. `GET /postings/{id}`
3. `GET /areas` (optional)
4. `GET /tags` (optional)

### 11.2 Connector
1. `POST /discoveries`
2. `POST /evidence`
3. optional signed webhook endpoints per connector (e.g. Apify)

### 11.3 Processor
1. `GET /jobs`
2. `POST /jobs/{id}/claim`
3. `POST /jobs/{id}/result`

### 11.4 Admin/moderation
1. `POST /modules`, `PATCH /modules/{id}`, credential rotation, disable.
2. `GET /candidates`, `PATCH /candidates/{id}` (approve/reject/merge/override).
3. `PATCH /postings/{id}`.
4. `GET /jobs`, `GET /discoveries/{id}` for audit.

## 12) LLM integration
1. Add `TaskRouter` for `extract_fields`, `extract_ner`, `summarize`.
2. Baseline adapter: LiteLLM in Python workers.
3. Enforce schema validation and confidence thresholds before patch application.
4. Keep adapter boundary so Bifrost/other gateways can be plugged later.

## 13) Security and compliance
1. Human auth (`user`, `moderator`, `admin`) uses Supabase Auth + RLS.
2. Bot auth is separate from Supabase user auth:
- machine credentials via `X-API-Key` or custom scoped JWT issuer
- credentials backed by `modules` table and scope checks
- avoid mixing machine sessions with human session tokens
3. Public endpoints are read-only.
4. Evidence URIs are never public.
5. Per-source ToS/robots policy config and kill switch.

## 14) Observability
1. OpenTelemetry across API and workers.
2. Primary sink: GCP Cloud Operations.
3. Alerts for:
- ingest failures
- queue backlog
- lease expiration growth
- dedupe anomalies
- freshness SLA misses
4. Keep OTLP exporter-ready config for future sinks.

## 15) Deployment
1. UI on Vercel.
2. API/workers on Cloud Run/Cloud Run Jobs.
3. Supabase Postgres/Auth as core data/auth platform.
4. CI/CD:
- build/deploy on push to main.
- migration step explicit and controlled.

## 16) SLAs and quality targets
1. Freshness: active posting re-check within 24h.
2. Moderation turnaround target: under 24h.
3. Dedupe: high precision target (>=98% on evaluated merge sample).
4. Public read API practical target: 99% monthly uptime.

## 17) Testing plan
1. Unit tests for URL normalization/hash/idempotency.
2. Unit tests for dedupe scoring components.
3. Integration tests for discovery -> candidate -> posting pipeline.
4. Integration tests for moderation and merge conflict paths.
5. Integration tests for lease reaper and retry behavior.
6. Security tests for scope and RLS enforcement.
7. E2E tests for catalogue filter/sort/detail and admin moderation flows.

## 18) Defaults and assumptions
1. Public catalogue with authenticated operations.
2. English-first extraction for v1.
3. Precision-first dedupe over aggressive recall.
4. No notifications/application tracking/sharing in v1.
5. Architecture is intentionally migratable to stronger orchestrators and optional alternate LLM/observability backends later.
