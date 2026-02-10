# Implementation Plan (v1.2 Spec)

## Legend
- Priority: `P0` critical path, `P1` important, `P2` useful after core stability.
- Complexity: `S` (1-2 days), `M` (3-5 days), `L` (1-2 weeks), `XL` (2+ weeks).
- Order: lower number means earlier on optimal critical path.

## Status Snapshot (2026-02-10)

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
| D3 | in_progress | Worker runtime now dispatches `check_freshness` with periodic scheduler-triggered enqueue, while structured logs/OTel and richer execution semantics are pending. |
| E1 | in_progress | Base URL normalization/hash logic exists; per-domain override support is pending. |
| E2 | not_started | Redirect resolution async job path is not implemented. |
| E3 | done | Dedupe scorer v1 now computes deterministic merge confidence from strong/medium/tie-break signals (URL/hash, text similarity, NER/contact-domain overlap). |
| E4 | done | Merge policy routing now records machine decisions (`auto_merged`/`needs_review`/`rejected`), auto-applies high-confidence merges, and routes uncertain/conflicting matches to moderation with provenance. |
| F1 | done | Moderation APIs now cover approve/reject (state patch), merge, and override flows with role checks + audit events. |
| F2 | in_progress | `source_trust_policy` routing now drives trusted/semi/untrusted publication paths and merge-outcome actions (`needs_review`/`rejected`/`auto_merged`) with source-specific moderation-route receipts; repository write-path validation now strictly enforces allowed merge actions, route-label format, and unknown-key rejection for merge-routing maps, while admin policy endpoints are still pending. |
| F3 | done | Posting lifecycle transitions are now explicit via moderated `PATCH /postings/{id}` with transition guards, candidate synchronization, provenance writes, and DB-backed integration coverage. |
| G1 | in_progress | `GET /postings` now supports detail/filter/sort/search/pagination with contract tests; additional relevance/edge-case query semantics remain to harden. |
| G2 | done | Freshness scheduler endpoint + worker cadence now enqueue `check_freshness` jobs; result/dead-letter paths apply deterministic posting downgrade/archive transitions with provenance and integration coverage. |
| H1 | in_progress | Minimal Next.js public shell exists; full catalogue UX pending. |
| H2 | not_started | Admin/moderator UI not implemented. |
| I1 | not_started | TaskRouter abstraction not implemented. |
| I2 | not_started | LiteLLM adapter not implemented. |
| J1 | not_started | OTel instrumentation not implemented. |
| J2 | not_started | Dashboards/alerts not implemented. |
| K1 | not_started | Connector SDK package not implemented. |
| K2 | not_started | RSS connector not implemented. |
| K3 | not_started | Telegram connector not implemented. |
| K4 | not_started | Apify connector not implemented. |
| K5 | not_started | Social connectors not implemented. |
| L1 | in_progress | Integration tests cover discovery/jobs/postings list+detail+filters, projection path, lease requeue, retry/dead-letter, freshness enqueue/dead-letter downgrade flow, moderation authz/state/merge/override, and posting lifecycle patch transitions; CI now runs DB-backed integration as a separate required job, while end-to-end UI moderation tests remain pending. |
| L2 | not_started | Load/perf testing not implemented. |
| M1 | in_progress | Quality CI is split into fast and DB-backed integration required checks; full deploy + migration gate pipeline remains pending. |
| M2 | not_started | Launch hardening checklist/runbook not complete. |

## Next Implementation Steps (Priority Order)

1. Continue `F2` trust-policy automation hardening around operator ergonomics and policy management surfaces.
- Deliver admin policy-management API contracts that call repository-validated writes (target surface: `GET /admin/source-trust-policy`, `PUT /admin/source-trust-policy/{source_key}`, `PATCH /admin/source-trust-policy/{source_key}` for enable/disable).
- Add contract tests for admin trust-policy writes that assert strict `rules_json` merge-routing validation responses (invalid action, invalid route label, unknown map keys).

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
| 18 | F2 | Trust-policy publisher (trusted/semi/untrusted logic) | P0 | M | F1, E4 | Policy engine for auto-publish routing; repository write path now validates merge-routing `rules_json` contract, admin endpoints remain pending. |
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
