# Implementation Plan (v1.2 Spec)

## Legend
- Priority: `P0` critical path, `P1` important, `P2` useful after core stability.
- Complexity: `S` (1-2 days), `M` (3-5 days), `L` (1-2 weeks), `XL` (2+ weeks).
- Order: lower number means earlier on optimal critical path.

## Status Snapshot (2026-02-09)

### Status legend
- `done`: implemented and validated in current repo/CI.
- `in_progress`: partially implemented; contract exists but key behavior is still missing.
- `not_started`: no meaningful implementation yet.

### Current task status

| ID | Status | Notes |
|---|---|---|
| A1 | done | Monorepo scaffold and service layout are in place. |
| A2 | done | Baseline schema + migration scripts are present and applied in CI/local flows. |
| A3 | in_progress | Seed/bootstrap scripts exist; full role bootstrap flow remains incomplete. |
| B1 | done | FastAPI skeleton and route wiring are in place. |
| B2 | done | Machine auth validates against `modules` + `module_credentials` with scope checks. |
| B3 | in_progress | Human role claims now resolve from trusted Supabase `app_metadata` fields only; production provisioning conventions still need finalization. |
| C1 | done | Discovery ingest API is DB-backed with idempotency behavior. |
| C2 | in_progress | Evidence metadata API is DB-backed; object store adapter is not implemented yet. |
| C3 | done | `extract` job completion now materializes `posting_candidates` + discovery/evidence links with provenance writes. |
| D1 | done | Job ledger API (`GET/claim/result`) is DB-backed. |
| D2 | done | Expired-lease requeue endpoint exists and workers trigger it periodically; failed results now follow bounded retry then dead-letter transitions. |
| D3 | in_progress | Worker scaffold exists; structured logs/OTel and richer execution semantics are pending. |
| E1 | in_progress | Base URL normalization/hash logic exists; per-domain override support is pending. |
| E2 | not_started | Redirect resolution async job path is not implemented. |
| E3 | not_started | Dedupe scorer is not implemented. |
| E4 | not_started | Merge decision flow is not implemented. |
| F1 | in_progress | Baseline moderation APIs exist (`GET /candidates`, `PATCH /candidates/{id}`) with role/scope checks; full moderation actions remain pending. |
| F2 | not_started | Trust-policy publication logic not implemented. |
| F3 | in_progress | `extract` job completion now projects baseline postings; lifecycle transitions (`stale/archived/closed`) remain pending. |
| G1 | in_progress | `GET /postings` exists; detail/filter/sort contracts are incomplete. |
| G2 | not_started | Freshness checker job flow not implemented. |
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
| L1 | in_progress | Integration tests cover discovery/jobs/postings-list, projection path, lease requeue, retry/dead-letter, and moderation authz allow/deny paths; full moderation pipeline tests pending. |
| L2 | not_started | Load/perf testing not implemented. |
| M1 | in_progress | Quality CI exists (lint/typecheck/tests); full deploy + migration gate pipeline pending. |
| M2 | not_started | Launch hardening checklist/runbook not complete. |

## Next Implementation Steps (Priority Order)

1. Complete `B3 + F1` authorization and moderation baseline.
- Finalize production Supabase role provisioning conventions (`app_metadata.role|sj_role|roles[]`) and operator runbook.
- Extend moderation actions beyond state patching (approve/reject/merge/override semantics).
- Add integration tests for moderation state transitions and posting lifecycle coupling.

2. Move `G1` from partial to production-ready.
- Add posting detail endpoint and filter/sort/search pagination behavior.
- Add API contract tests for query correctness and response stability.

3. Strengthen `M1 + L1` delivery safety.
- Keep DB-backed integration tests required in CI.
- Split fast vs integration test jobs and document required branch checks.

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
| 18 | F2 | Trust-policy publisher (trusted/semi/untrusted logic) | P0 | M | F1, E4 | Policy engine for auto-publish routing. |
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
