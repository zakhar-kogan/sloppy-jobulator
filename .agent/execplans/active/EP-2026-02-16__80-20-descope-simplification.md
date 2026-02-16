# Plan ID: EP-2026-02-16__80-20-descope-simplification

- Status: `ACTIVE`
- Created: `2026-02-16`
- Last Updated: `2026-02-16`
- Owner: `Codex`

## Purpose / Big Picture
Reduce implementation complexity to match the product domain (PhD/research jobs aggregator) while keeping a working system online. Target outcome: faster iteration on the 4 core surfaces (`public table`, `admin queue`, `connectors`, `auth`) without a rewrite.

## Scope and Constraints
- In scope:
  - Freeze or hide non-essential enterprise controls.
  - Narrow runtime paths for dedupe/job orchestration/audit to practical defaults.
  - Refactor repository into capability modules with no behavior drift.
  - Keep current API contracts working where possible; deprecate gradually.
- Out of scope:
  - New feature expansion (advanced ranking, keyboard workflows, broad connector marketplace).
  - Full architecture rewrite or data model replacement.
- Constraints:
  - Preserve production/staging operability during simplification.
  - Prefer additive compatibility + feature flags before deletion.
  - Each phase must ship independently with rollback-safe toggles.

## Progress
- [x] Define simplification objective and non-goals.
- [x] Phase A: freeze policy surface and hide advanced controls.
- [ ] Phase B: simplify dedupe + jobs runtime behavior.
- [ ] Phase C: trim provenance/event volume to operator-relevant events.
- [ ] Phase D: split repository by bounded contexts (no behavior change first).
- [ ] Validate and retire obsolete paths.

## Decision Log
- 2026-02-16: Use a staged de-scope plan (freeze -> simplify -> prune) instead of a rewrite to avoid delivery stall.
- 2026-02-16: Implement Phase A normalization in admin route (ignore advanced `rules_json` payload; derive `requires_moderation` from simplified defaults) while leaving repository-level advanced machinery intact for later removal phases.

## Plan of Work
1. Phase A: Policy surface freeze (low risk, immediate complexity win)
   - Goal: make trust-policy behavior effectively single-profile by default.
   - Actions:
     - Introduce one global default policy profile and route current policy fields to fixed defaults unless explicitly overridden by admin.
     - Hide advanced trust-policy controls in UI (`merge_decision_actions`, `moderation_routes`, granular rule maps).
     - Keep only minimal toggles visible: `enabled`, optional `auto_publish`.
   - Touched paths (expected):
     - `web/app/admin/source-trust-policy/**`
     - `api/app/api/routes/admin.py`
     - `api/app/services/repository.py`

2. Phase B: Runtime simplification for ingestion throughput
   - Goal: keep core flow reliable with fewer operational states.
   - Actions:
     - Narrow dedupe to practical checks: exact normalized URL/hash + simple similarity threshold.
     - Route uncertain matches directly to `needs_review` without deep policy matrix branches.
     - Reduce active job lifecycle to essential path (`queued -> claimed -> done/failed`); keep dead-letter/reap disabled by default.
   - Touched paths (expected):
     - `api/app/services/dedupe.py`
     - `api/app/services/repository.py`
     - `api/app/api/routes/jobs.py`
     - `workers/app/**`

3. Phase C: Audit/provenance trimming
   - Goal: retain useful operator evidence while dropping noisy internal event spam.
   - Actions:
     - Keep provenance for admin/human actions and publish/unpublish transitions.
     - Stop emitting low-value machine/internal transition events unless needed for debugging.
     - Add one debug flag to re-enable verbose eventing when investigating incidents.
   - Touched paths (expected):
     - `api/app/services/repository.py`
     - `docs/runbook`/operator notes as needed

4. Phase D: Repository decomposition (structure-only first)
   - Goal: reduce cognitive load from monolith repository file.
   - Actions:
     - Split into bounded modules:
       - `candidate_repository.py`
       - `posting_repository.py`
       - `jobs_repository.py`
       - `admin_repository.py`
       - shared `repository_base.py` for pool/transaction helpers.
     - First pass: move code with identical behavior/tests.
     - Second pass: simplify per module after move.
   - Touched paths (expected):
     - `api/app/services/repository.py` (shrink to facade or compatibility layer)
     - `api/app/services/repository_*.py` (new files)

5. Deletion and deprecation pass
   - Goal: remove complexity debt after replacement paths are stable.
   - Actions:
     - Mark unused config/env vars and policy fields deprecated.
     - Remove dead UI/API branches after one release cycle.
     - Update docs/specs to match the simplified domain scope.

## Validation and Acceptance
- Functional acceptance (must stay true after each phase):
  - Public catalogue lists postings and details page works.
  - Admin queue can filter and mutate candidate state.
  - At least one connector path can ingest and create reviewable candidates.
  - Non-admin callers cannot mutate admin resources.
- Command baseline (per phase):
  - `uv run --project api --extra dev pytest api/tests/test_candidates_authz.py -q`
  - `uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "candidates or postings or trust_policy" -q`
  - `fnm exec --using 24.13.0 pnpm --dir web run test:contracts`
  - `fnm exec --using 24.13.0 pnpm --dir web run typecheck`

## Idempotence and Recovery
- Every phase lands behind defaults/flags where practical.
- If regressions appear, revert phase-specific diffs without undoing prior stabilized phases.
- Keep compatibility wrappers until downstream callers are migrated.

## Outcomes and Retrospective
- Phase A shipped:
  - Source trust policy admin UI now exposes only minimal controls (`source_key`, `trust_level`, `auto_publish`, `enabled`).
  - Admin PUT route now enforces a simple policy profile (`rules_json={}` and derived moderation requirement) instead of user-specified advanced rule maps.
  - Integration tests for admin trust-policy CRUD updated and passing under DB-backed run.
- Success metric: reduced policy/runtime surface area with unchanged 4-core user flows.
