# Implementation Plan (v1.2 Spec)

## Legend
- Priority: `P0` critical path, `P1` important, `P2` useful after core stability.
- Complexity: `S` (1-2 days), `M` (3-5 days), `L` (1-2 weeks), `XL` (2+ weeks).
- Order: lower number means earlier on optimal critical path.

## Status Snapshot (2026-02-16)

### Status legend
- `done`: implemented and validated in current repo/CI.
- `in_progress`: partially implemented; contract exists but key behavior is still missing.
- `not_started`: no meaningful implementation yet.

### Current task status

| ID | Status | Notes |
|---|---|---|
| A1 | done | Monorepo scaffold and service layout are in place. |
| A2 | done | Baseline schema + migration scripts are present and applied in CI/local flows. |
| A3 | in_progress | Bootstrap script now emits deterministic Supabase SQL by user id/email; full environment provisioning automation remains pending. |
| B1 | done | FastAPI skeleton and route wiring are in place. |
| B2 | done | Machine auth validates against `modules` + `module_credentials` with scope checks. |
| B3 | done | Human role claims resolve only from trusted Supabase `app_metadata` fields, with provisioning conventions captured in runbook. |
| C1 | done | Discovery ingest API is DB-backed with idempotency behavior. |
| C2 | in_progress | Evidence metadata API is DB-backed; object store adapter is not implemented yet. |
| C3 | done | `extract` job completion now materializes `posting_candidates` + discovery/evidence links with provenance writes. |
| D1 | done | Job ledger API (`GET/claim/result`) is DB-backed. |
| D2 | done | Expired-lease requeue endpoint exists and workers trigger it periodically; failed results now follow bounded retry then dead-letter transitions. |
| D3 | in_progress | Worker runtime dispatches `check_freshness` with periodic scheduler-triggered enqueue; structured logging + OTel baseline instrumentation is now wired, with richer execution semantics still pending. |
| E1 | in_progress | Base URL normalization/hash logic exists; per-domain override support is pending. |
| E2 | in_progress | Redirect execution path is now operator-visible in cockpit jobs: admin jobs contract exposes `inputs_json/result_json/error_json`, repository stamps `repository_outcome` (`applied` / `conflict_skipped` / `unchanged`), and cockpit surfaces retry windows + redirect conflict/outcome diagnostics; remaining work is rollout/default tuning and broader live revalidation. |
| E3 | done | Dedupe scorer v1 now computes deterministic merge confidence from strong/medium/tie-break signals (URL/hash, text similarity, NER/contact-domain overlap). |
| E4 | done | Merge policy routing now records machine decisions (`auto_merged`/`needs_review`/`rejected`), auto-applies high-confidence merges, and routes uncertain/conflicting matches to moderation with provenance. |
| F1 | done | Moderation APIs now cover approve/reject (state patch), merge, and override flows with role checks + audit events. |
| F2 | done | `source_trust_policy` routing now drives trusted/semi/untrusted publication paths and merge-outcome actions (`needs_review`/`rejected`/`auto_merged`) with source-specific moderation-route receipts; repository write-path validation strictly enforces allowed merge actions, route-label format, and unknown-key rejection; admin policy endpoints (`GET/PUT/PATCH /admin/source-trust-policy`) plus provenance audit events (`policy_upserted`, `policy_enabled_changed`) are implemented, with fallback policy defaults aligned to confidence-based trusted/semi-trusted behavior and DB-backed integration coverage passing. |
| F3 | done | Posting lifecycle transitions are now explicit via moderated `PATCH /postings/{id}` with transition guards, candidate synchronization, provenance writes, and DB-backed integration coverage. |
| G1 | in_progress | `GET /postings` now supports detail/filter/sort/search/pagination with contract tests; additional relevance/edge-case query semantics remain to harden. |
| G2 | done | Freshness scheduler endpoint + worker cadence now enqueue `check_freshness` jobs; result/dead-letter paths apply deterministic posting downgrade/archive transitions with provenance and integration coverage. |
| H1 | in_progress | Public surface advanced from scaffold to API-backed catalogue/search UX on `/` with filters, sort, pagination, and detail preview via new public proxy routes (`/api/postings`, `/api/postings/{id}`); additional relevance tuning and visual polish remain. |
| H2 | in_progress | Cockpit now includes bulk candidate patch flow, per-row multi-select controls, transition guardrail messaging, clearer loading/empty/error table states, and redirect/retry diagnostics in jobs table while preserving existing API contracts. |
| I1 | not_started | TaskRouter abstraction not implemented. |
| I2 | not_started | LiteLLM adapter not implemented. |
| J1 | in_progress | OTel baseline is wired for API/workers (FastAPI + asyncpg + httpx spans, worker lifecycle spans, trace/log correlation, OTLP exporter-ready config); telemetry validation script now uses API health fallback probing plus Cloud Monitoring REST queries (CLI-version resilient), and current staging check shows missing worker backlog series for configured worker service label. |
| J2 | in_progress | Cloud Operations dashboard + alert policy artifacts are versioned and now have environment-bindable templates/import scripts (`docs/observability/*.template.*`, `scripts/import-observability-assets.sh`); real staging/prod channel + label values still depend on secret bindings. |
| K1 | not_started | Connector SDK package not implemented. |
| K2 | not_started | RSS connector not implemented. |
| K3 | not_started | Telegram connector not implemented. |
| K4 | not_started | Apify connector not implemented. |
| K5 | not_started | Social connectors not implemented. |
| L1 | done | Live E2E coverage now spans bulk moderation and legacy cockpit flows with deterministic queue-selection fixtures aligned to current candidate-state transitions; DB-backed targeted API redirect/admin/trust/postings integration slices and full live cockpit suite pass. |
| L2 | not_started | Load/perf testing not implemented. |
| M1 | in_progress | Quality CI is split into fast and DB-backed integration checks with explicit `migration-safety` + `deploy-readiness-gate`, and a staged `deploy.yml` workflow now binds env-specific secrets/commands; first live staging/prod executions remain pending. |
| M2 | not_started | Launch hardening checklist/runbook not complete. |

## Next Implementation Steps (Priority Order)

1. Close remaining `J1/J2/M1` environment bindings after baseline merge:
- Validate OTLP sink + telemetry quality in staging (`J1`).
- Bind dashboard/alert policies to production metric labels and notification channels (`J2`).
- Add environment-specific deploy execution workflow behind existing `deploy-readiness-gate` (`M1`).
2. Continue `H2` cockpit hardening around operator ergonomics (bulk action observability, faster triage loops) while preserving existing API contracts.
3. Keep `G1/H1` focused on relevance/edge-case query semantics and catalogue UX polish against current API contracts.

## Workstreams and Task Graph

| Order | ID | Task | Priority | Complexity | Depends On | Notes |
|---|---|---|---|---|---|---|
| 1 | A1 | Repo bootstrap (`api/`, `web/`, `workers/`, `db/`, `docs/`) | P0 | S | - | Monorepo layout + tooling contracts. |
| 2 | A2 | Apply DB schema + migration pipeline | P0 | M | A1 | Use `db/schema_v1.sql` as baseline migration. |
| 3 | A3 | Seed taxonomy and role bootstrap scripts | P0 | S | A2 | Sector/degree/opportunity enums + admin bootstrap. |
| 4 | B1 | FastAPI skeleton + health/auth middleware | P0 | M | A1, A2 | Human vs machine auth split from day one. |
| 5 | B2 | Machine auth (`X-API-Key` + modules/scopes) | P0 | M | B1, A2 | Credentials table + scope guards. |
| 6 | B3 | Human auth integration (Supabase JWT + role checks) | P0 | M | B1, A2 | `user/moderator/admin` policy checks. |
| 7 | C1 | Discovery ingest API (`POST /discoveries`, idempotency) | P0 | M | B2, A2 | Unique keys and canonical URL/hash writes. |
| 8 | C2 | Evidence API (`POST /evidence`) + object store adapter | P0 | M | B2, A2 | Metadata-only in DB, URI pointers to blobs. |
| 9 | C3 | Candidate materialization + provenance event writes | P0 | M | C1, A2 | Append-only discovery flow. |
| 10 | D1 | Job ledger API (`GET/claim/result`) | P0 | M | B2, A2 | Leases, attempts, status transitions. |
| 11 | D2 | Lease reaper scheduler + backoff/jitter polling | P0 | S | D1 | Prevent stuck claimed jobs. |
| 12 | D3 | Worker runtime scaffold (Python) | P0 | M | D1 | Shared worker loop + structured logs + OTel. |
| 13 | E1 | URL normalization library (safe + per-domain overrides) | P0 | M | C1 | Conservative normalization only. |
| 14 | E2 | Redirect resolution async job (`resolve_url_redirects`) | P0 | S | D3, E1 | Never on ingest path. |
| 15 | E3 | Dedupe scorer v1 (URL/hash + text sim + NER tie-break) | P0 | L | C3, D3, E1 | Precision-first thresholds + confidence output. |
| 16 | E4 | Merge decision flow (auto vs review queue) | P0 | M | E3, C3 | Write `candidate_merge_decisions` + provenance. |
| 17 | F1 | Moderation APIs (approve/reject/merge/override) | P0 | M | B3, E4, A2 | Staff-only operations. |
| 18 | F2 | Trust-policy publisher (trusted/semi/untrusted logic) | P0 | M | F1, E4 | Policy engine for auto-publish routing; repository write path validates merge-routing `rules_json`, admin `GET/PUT/PATCH /admin/source-trust-policy` endpoints are available, and admin writes emit provenance audit events. |
| 19 | F3 | Posting projection + status lifecycle | P0 | M | F2 | `active/stale/archived/closed` handling. |
| 20 | G1 | Public read APIs (`GET /postings`, detail, filters) | P0 | M | F3 | Search/filter/sort/pagination. |
| 21 | G2 | Daily freshness checker jobs + archive transitions | P0 | M | D3, F3 | 24h cadence + retries before downgrade. |
| 22 | H1 | Next.js public catalogue (table + filters + detail) | P1 | L | G1 | Core user-facing browsing experience. |
| 23 | H2 | Admin/moderator UI (queue, merges, modules, jobs) | P1 | L | F1, G1 | Operator cockpit. |
| 24 | I1 | LLM TaskRouter abstraction (extract/NER/summarize) | P1 | M | D3 | Provider-agnostic interface and contracts. |
| 25 | I2 | LiteLLM adapter + schema/confidence guards | P1 | M | I1 | Production default for processors. |
| 26 | J1 | OTel instrumentation (API/workers/db/client) | P0 | M | B1, D3 | Logs/metrics/traces baseline. |
| 27 | J2 | GCP dashboards + SLO alerts | P0 | S | J1 | Ingest failures, backlog, SLA misses. |
| 28 | K1 | Connector SDK contract package (Python) | P1 | M | C1, C2, D1 | Make new connectors cheap to build. |
| 29 | K2 | RSS connector | P1 | S | K1 | First low-friction source adapter. |
| 30 | K3 | Telegram connector | P1 | M | K1 | Message idempotency + metadata mapping. |
| 31 | K4 | Apify webhook/source connector | P1 | M | K1 | Hard-site scraping bridge. |
| 32 | K5 | Social connectors (X/Bluesky API-first + fallback policy) | P2 | L | K1 | Enable with explicit per-source policy controls. |
| 33 | L1 | E2E + integration test suite | P0 | L | G1, F1, D1 | Pipeline correctness + auth + moderation. |
| 34 | L2 | Load/perf test (~100 sources/day) | P1 | M | L1 | Queue contention and dedupe throughput. |
| 35 | M1 | CI/CD pipelines (API/web/workers/db migration gates) | P0 | M | A1, A2 | Prevent unsafe deploys. |
| 36 | M2 | Launch hardening checklist + runbook | P1 | S | J2, L1 | On-call docs + rollback playbook. |

## Optimal Implementation Order (Execution Phases)

### Phase 1: Foundation and contracts (Weeks 1-2)
- A1, A2, A3, B1, B2, B3
- Outcome: skeleton system with auth boundaries and durable schema.

### Phase 2: Ingestion and durable processing core (Weeks 2-4)
- C1, C2, C3, D1, D2, D3, E1, E2
- Outcome: connector intake works, jobs are durable, URL handling is correct.

### Phase 3: Dedupe, moderation, publishing (Weeks 4-6)
- E3, E4, F1, F2, F3, G1, G2
- Outcome: quality pipeline from raw discoveries to public postings.

### Phase 4: Product surfaces and operations (Weeks 6-8)
- H1, H2, J1, J2, M1
- Outcome: usable product + observability + deploy safety.

### Phase 5: Intelligence and source expansion (Weeks 8-10)
- I1, I2, K1, K2, K3, K4
- Outcome: LLM extraction router + first practical connector set.

### Phase 6: Scale and hardening (Weeks 10-12)
- K5, L1, L2, M2
- Outcome: stable at target scale with release/incident readiness.

## Critical Path (Must-not-slip)
1. `A2 -> B2 -> C1 -> D1 -> D2 -> E3 -> F2 -> F3 -> G1 -> G2 -> J2 -> L1`
2. If delayed, launch readiness and data quality are both blocked.

## Parallelization Opportunities
1. Web UI (`H1/H2`) can begin once API contracts (`G1/F1`) stabilize.
2. OTel (`J1`) can start as soon as API + worker skeleton exist (`B1/D3`).
3. Connector SDK and basic connectors (`K1/K2`) can run parallel to moderation UI.

## Risk Register (top)
1. Dedupe false merges: mitigate with precision-first thresholds + mandatory review band.
2. Queue starvation/job leaks: mitigate with lease reaper, visibility dashboards, DLQ policy.
3. Source volatility/ToS changes: mitigate with per-source kill switch + trust policies.
4. LLM extraction drift: mitigate with schema validation + confidence gates + regression eval set.

## Definition of Done (v1 launch)
1. Public catalogue is usable and performant.
2. Connectors ingest with idempotency and provenance.
3. Daily freshness and archive lifecycle operational.
4. Moderation and trust-based publication working.
5. Alerts fire for core failures; runbook exists.
6. End-to-end tests pass on CI.
