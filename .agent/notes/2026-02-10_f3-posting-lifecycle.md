# Task Note: 2026-02-10 f3-posting-lifecycle

## Task
- Request: proceed with the next roadmap step and start `F3`.
- Scope: implement posting lifecycle transitions (`active/stale/archived/closed`) beyond baseline projection and add integration coverage for downgrade/reopen semantics.
- Constraints: keep contracts stable for existing public read endpoints and preserve candidate moderation behavior.

## Actions Taken
1. Added posting lifecycle patch contract (`PostingPatchRequest`) and route (`PATCH /postings/{posting_id}`) with human moderation auth (`moderation:write`).
2. Implemented repository mutation `update_posting_status` with:
- explicit posting transition guards,
- deterministic candidate-state synchronization (`published/archived/closed`),
- transactional updates with provenance event writes.
3. Added helper methods for posting transition validation and posting->candidate mapping.
4. Added DB-backed integration tests for:
- valid lifecycle path (`active -> stale -> archived -> active`) with candidate sync,
- invalid transition conflict (`closed -> active`).
5. Ran targeted integration tests, non-integration API tests, lint, and typecheck.

## What Went Wrong
1. Issue: first integration test run failed before assertions.
- Root cause: local Postgres container was not running (`localhost:5432` connection refused).
- Early signal missed: test command assumed active DB from prior session.
- Prevention rule: run `make db-up && make db-reset` before DB-backed test commands in new sessions.

## What Went Right
1. Improvement: posting lifecycle changes are now explicit API operations with auditability and deterministic coupling to candidate states.
- Evidence (manageability/modularity): lifecycle logic is centralized in repository transition helpers, and integration coverage validates both happy path and guardrails.
- Why it worked: implementing lifecycle state machine in one transactional write path prevented drift between posting and candidate records.
2. Improvement: roadmap `F3` stale-status gap is closed without schema changes.
- Evidence (time/readability): additive route + repository method reused existing auth/provenance patterns, reducing implementation overhead.
- Why it worked: existing moderation and provenance scaffolding was already aligned with human-authenticated state transitions.

## Reusable Learnings
1. Learning: model lifecycle transitions with explicit per-entity state machines and enforce them at repository transaction boundaries.
- Promotion decision: `promote now`
- Promote to: `PATTERNS.md`
- Why: this pattern is reusable for `G2` freshness-driven transitions and future posting/admin workflows.
2. Learning: include at least one invalid-transition integration test for every new lifecycle endpoint.
- Promotion decision: `pilot backlog`
- Why: strong guardrail, but should be observed across additional endpoints before formal promotion.
3. Learning: DB-backed integration setup failures are mostly environment bootstrapping, not code regressions.
- Promotion decision: `keep local`
- Why: already covered by existing runbook workflows and not a new project-wide pattern.

## Receipts
- Commands run:
- `make db-up`
- `make db-reset`
- `SJ_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sloppy_jobulator DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sloppy_jobulator uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "posting_lifecycle_patch or moderation_candidate_state_transitions_update_posting_status"`
- `uv run --project api --extra dev pytest api/tests --ignore=api/tests/test_discovery_jobs_integration.py`
- `uv run --project api --extra dev ruff check api/app api/tests && uv run --project api --extra dev mypy api/app`
- `make db-down`
- Files changed:
- `api/app/schemas/postings.py`
- `api/app/api/routes/postings.py`
- `api/app/services/repository.py`
- `api/tests/test_discovery_jobs_integration.py`
- `api/tests/test_candidates_authz.py`
- `.agent/execplans/INDEX.md`
- `.agent/execplans/archive/EP-2026-02-10__f3-posting-lifecycle.md`
- `.agent/notes/2026-02-10_f3-posting-lifecycle.md`
- Tests/checks:
- Targeted integration tests passed (`3/3` selected).
- Non-integration API tests passed (`15/15`).
- API lint/typecheck passed.
