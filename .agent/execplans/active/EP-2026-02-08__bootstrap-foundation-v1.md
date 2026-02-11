# ExecPlan: EP-2026-02-08__bootstrap-foundation-v1

## Metadata
- Status: `ACTIVE`
- Created: `2026-02-08`
- Updated: `2026-02-11`
- Owner: `Codex`

## Purpose / Big Picture
Bootstrap this repository into a real project implementation using the handoff spec and implementation plan, with a concrete Phase 1 foundation that is runnable and reviewable.

## Scope and Constraints
- In scope:
1. Keep spec/plan docs repo-local under `docs/spec/` and `docs/roadmap/`.
2. Create monorepo service layout and baseline implementation files.
3. Add initial DB schema/migration and seed.
4. Add starter API endpoints, worker runtime scaffold, and web shell.
5. Update agent project-mode state files for continuity.
- Out of scope:
1. Full Supabase/RLS integration.
2. Production deployment IaC.
3. Complete moderation/admin feature set.
- Constraints:
1. Preserve spec-aligned contracts while keeping diffs reviewable.
2. Avoid host-level installs.
3. Report validation gaps explicitly.

## Progress
- [x] Clarify source of handoff files and copy to local repo.
- [x] Scaffold monorepo directories and root commands.
- [x] Add baseline DB schema + migration + seed.
- [x] Add FastAPI skeleton and worker scaffold.
- [x] Add Next.js catalogue shell.
- [x] Wire API/worker to Postgres and Supabase auth.
- [x] Implement discovery/evidence persistence with provenance writes.
- [x] Add CI workflow for api/workers/web lint/typecheck/tests gates.
- [x] Add API integration tests for discovery->job claim/result flow and CI Postgres provisioning.
- [x] Add local Postgres compose/make workflow and extend integration coverage to postings list path.
- [x] Harden postings list edge semantics (trimmed filters, case-insensitive tag match, deterministic tie-breaks, null-last deadline/published sorts) with integration coverage.
- [x] Split CI into fast checks vs DB-backed integration required checks (`M1 + L1`).
- [x] Start `A3/F2` baseline: role bootstrap SQL automation + trust-policy-based publish routing with integration coverage.
- [x] Implement `E3` dedupe scorer v1 and wire deterministic merge confidence/risk outputs into `E4` merge policy routing with auto-merge/review decision recording.
- [x] Expand `F2` merge-aware trust-policy routing with source-configurable merge actions/reasons/moderation routes and DB-backed integration coverage.
- [x] Add strict repository validation + write-path enforcement for trust-policy merge-routing `rules_json` keys (allowed actions, route-label format, unknown-key rejection).
- [x] Expand `F2` integration regressions with mixed trust + conflicting dedupe signals and invalid policy-write validation cases.
- [x] Expose admin trust-policy management API surface (`GET/PUT/PATCH /admin/source-trust-policy`) wired to repository-validated writes with DB-backed contract tests.
- [x] Emit provenance audit events for admin trust-policy writes/toggles and assert them in DB-backed integration tests.
- [x] Add runbook API-first operator guidance for trust-policy management and audit verification (`curl` + SQL receipts).
- [x] Wire admin UI (`H2`) trust-policy management flows to `GET/PUT/PATCH /admin/source-trust-policy` via Next.js proxy routes.
- [x] Expand `H2` with operator cockpit baseline (`/admin/cockpit`) for candidate queue actions (`approve/reject/merge/override`) plus module/job visibility and bounded maintenance mutations via new admin API surfaces.
- [x] Expand `L1` live cockpit Playwright coverage with negative/authz scenarios (`409` merge conflict surfaced in UI, backend `401` missing bearer, `403` non-admin, `422` invalid payload).
- [x] Expand `L1` live cockpit persistence assertions for merge/override/module/job actions (candidate events, module mutation timestamps, enqueue/reap job-state transitions).
- [x] Harden `web-e2e-live` CI runtime with cache-backed dependencies/browsers, scoped retry, and explicit timeout budgets.
- [x] Add web API contract tests for admin proxy failure mapping (backend `4xx/5xx` passthrough, `limit` bounds pass-through, stable non-JSON error body shape).
- [x] Harden `H2` cockpit operator guardrails/ergonomics with transition-constrained patch options and reason-required merge/override + terminal patch actions.
- [x] Expand `L1` moderation/admin Playwright coverage (mock + live) for cockpit guardrails and reason-gated mutation flows.

## Decision Log
- 2026-02-08: Chose in-memory bootstrap for API/worker while committing canonical SQL schema.
- 2026-02-08: Replaced in-memory API persistence/auth stubs with Postgres-backed repository and real credential verification.
- 2026-02-08: Moved handoff docs into permanent `docs/spec` and `docs/roadmap` locations to remove `handoff/`.
- 2026-02-08: Standardized Node workflows on `fnm` + `pnpm` and committed lockfile-backed web installs.
- 2026-02-08: Added integration coverage for discovery->job flow with CI-managed Postgres service.
- 2026-02-08: Added local compose + make commands for integration DB lifecycle and expanded integration tests to `/postings`.
- 2026-02-08: Hardened local DB scripts for environments without host `psql` and stabilized API test lifecycle with lifespan-managed repository cleanup.
- 2026-02-09: Materialized `extract` job results into candidates/postings with provenance writes and DB-backed integration assertions.
- 2026-02-09: Completed D2 reliability baseline with API lease reaper + retry/dead-letter transitions and worker-triggered reaper loop.
- 2026-02-09: Started `B3 + F1` baseline with trusted Supabase app-metadata role contract and moderation candidate endpoints + authz tests.
- 2026-02-09: Expanded `B3 + F1 + G1` with moderation transition semantics and postings detail/filter/sort/search/pagination contracts + integration tests.
- 2026-02-09: Added moderation merge/override execution paths with provenance audit retrieval and DB-backed conflict/override integration coverage.
- 2026-02-09: Documented Supabase role-provisioning conventions in runbook so elevated role assignment is deterministic and aligned with API claim resolution.
- 2026-02-09: Hardened `G1` query semantics for whitespace-only filters, case-insensitive tag filtering, deterministic sort tie-break behavior, and null-last handling for `deadline/published_at` with DB-backed test assertions.
- 2026-02-09: Split CI API checks into `api-fast` and `api-integration-db`; documented required branch checks in README.
- 2026-02-09: Added `source_trust_policy` resolution in extract projection so publish decisions route to `published` vs `needs_review`, and added integration coverage for trusted/semi-trusted/untrusted plus source-key override paths.
- 2026-02-09: Replaced placeholder admin bootstrap script with deterministic role/provenance SQL generation (`--user-id|--email`, `--role`) and documented invocation in README/runbook.
- 2026-02-10: Added `E3` dedupe scorer module and integrated `E4` machine routing so extract projection now performs precision-first auto-merge/review/reject decisions with audited `candidate_merge_decisions` + provenance.
- 2026-02-10: Extended `F2` trust-policy handling to consume final merge decisions (`needs_review`, `rejected`, `auto_merged`) with `rules_json` overrides (`merge_decision_actions`, `merge_decision_reasons`, `moderation_routes`) and source-specific integration tests.
- 2026-02-10: Added forced auto-merge-conflict integration coverage to validate `auto_merge_blocked` fallback routing still honors source policy overrides and moderation-route receipts.
- 2026-02-10: Documented operator SQL runbook examples for `rules_json` merge-routing patterns, including `auto_merge_blocked` fallback/reason/route verification queries.
- 2026-02-10: Added strict `source_trust_policy` write validation in repository (`upsert_source_trust_policy`) and moved integration upserts through this path, then added mixed-trust/conflicting-signal and invalid-rules regression tests.
- 2026-02-10: Added admin trust-policy API endpoints for list/upsert/enable-toggle, backed by repository validation and covered with integration tests for success, authz, and invalid-rules responses.
- 2026-02-10: Added provenance event writes for admin trust-policy upsert/enable changes and extended admin integration tests to assert emitted audit payloads/actor attribution.
- 2026-02-10: Expanded runbook with API-based trust-policy operator flow (admin `GET/PUT/PATCH`) and provenance verification query patterns to reduce SQL-only policy management.
- 2026-02-10: Added `web/app/admin/source-trust-policy` UI and Next.js server proxy routes (`web/app/api/admin/source-trust-policy/**`) so operators can list/upsert/toggle policies against the admin API surface.
- 2026-02-10: Added admin module/job API endpoints (`GET/PATCH /admin/modules`, `GET /admin/jobs`, `POST /admin/jobs/reap-expired`, `POST /admin/jobs/enqueue-freshness`) plus `/admin/cockpit` UI and proxy routes for candidate queue actions and operator maintenance flows.
- 2026-02-10: Added web-side API-contract tests (`node:test`) for cockpit query serialization and proxy-path builders, wired as `pnpm --dir web test:contracts`.
- 2026-02-10: Added live cockpit negative/authz coverage in Playwright (`web/tests-e2e/admin-cockpit.live.spec.ts`) for merge-conflict error rendering and backend `401/403/422` contracts.
- 2026-02-10: Expanded live cockpit persistence assertions in Playwright to assert candidate provenance events (`merge_applied`, `merged_away`, `state_overridden`), module toggle `updated_at` progression, and enqueue/reap job ledger transitions.
- 2026-02-10: Hardened `.github/workflows/ci.yml` `web-e2e-live` with uv/pnpm/Playwright caching, explicit timeout budgets, and single-step retry-once logic for transient E2E startup failures.
- 2026-02-10: Switched `web/playwright.live.config.ts` to cached Chromium (`channel` removed), set CI `globalTimeout` budget, and disabled blanket CI per-test retries in favor of scoped job-step retry.
- 2026-02-10: Added `web/tests/admin-proxy-failure-mapping.test.ts` contracts and extracted `web/lib/admin-api-core.ts` so admin proxy passthrough/error-shape behavior is verified in `node:test` without Next runtime imports.
- 2026-02-11: Added cockpit guardrail UX in `moderator-cockpit-client` (patch transition options based on selected candidate state, required reasons for merge/override and terminal patch states, merge quick-pick selector) with contract + mock/live Playwright coverage.

## Plan of Work
1. Foundation bootstrap
- Deliverable: root project files and service directories.
- Paths: `README.md`, `Makefile`, `.gitignore`, `api/`, `workers/`, `web/`, `db/`.
2. Data model baseline
- Deliverable: complete v1 SQL schema and first migration.
- Paths: `db/schema_v1.sql`, `db/migrations/0001_schema_v1.sql`, `db/seeds/001_taxonomy.sql`.
3. Service skeletons
- Deliverable: API endpoints, worker loop, web shell page.
- Paths: `api/app/**`, `workers/app/**`, `web/app/**`.
4. Project-mode capture
- Deliverable: updated continuity/context/runbook and active plan registry.
- Paths: `.agent/CONTINUITY.md`, `.agent/CONTEXT.md`, `.agent/RUNBOOK.md`, `.agent/execplans/**`.

## Validation and Acceptance
1. `python -m compileall api/app workers/app`
- Expected: compile succeeds with no syntax errors.
2. `bash scripts/agent-hygiene-check.sh --mode project`
- Expected: passes in project mode.
3. `git status --short`
- Expected: only intended file changes.

## Idempotence and Recovery
1. File creation is idempotent; reruns overwrite with deterministic content.
2. DB schema is migration-based and can be applied via `scripts/apply_db_schema.sh`.
3. If bootstrap endpoints cause regressions, revert only service-scoped files without touching migration baseline.

## Outcomes and Retrospective
- Outcome: `IN_PROGRESS`
- Follow-ups:
1. Continue `L1` moderation/admin E2E breadth (additional filter/pagination edge cases, multi-candidate queue workflows, and trust-policy/admin-surface cross-flow scenarios).
2. Move next to `J1/J2/M1` hardening track (observability + dashboards/alerts + deploy/migration gate completeness) per implementation-plan critical path.
