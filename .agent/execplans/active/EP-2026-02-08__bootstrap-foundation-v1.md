# ExecPlan: EP-2026-02-08__bootstrap-foundation-v1

## Metadata
- Status: `ACTIVE`
- Created: `2026-02-08`
- Updated: `2026-02-09`
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
1. Harden postings query semantics and CI gate split for fast vs DB-backed integration suites.
2. Start role/bootstrap automation (`A3`) and trust-policy publication logic (`F2`).
