# Task Note: 2026-02-09 a3-f2-bootstrap-policy

## Task
- Request: start roadmap slice `A3/F2` by shipping role/bootstrap automation and trust-policy publish routing, then open a PR and verify split CI lanes.
- Scope: implement `source_trust_policy`-driven publish decisions in API extraction flow, add tests, upgrade bootstrap role script, update docs/agent state, and configure branch protection check contexts.
- Constraints: keep fast vs DB-backed CI lanes separate and preserve existing moderation/public contracts.

## Actions Taken
1. Enabled GitHub `main` branch protection required checks with contexts:
- `api-fast`
- `api-integration-db`
- `workers`
- `web`
- `validate-agent-contract`
2. Added trust-policy routing in `api/app/services/repository.py`:
- resolve effective policy from `source_trust_policy` (`source_key` override -> `module:<module_id>` -> `default:<trust_level>` fallback).
- evaluate auto-publish vs moderation routing and set candidate/posting defaults (`published/active` vs `needs_review/archived`).
- emit `provenance_events` with `event_type='trust_policy_applied'`.
3. Added DB-backed integration coverage for trusted confidence gate, semi-trusted auto-publish, untrusted moderation, and source-key override behavior.
4. Replaced placeholder `scripts/bootstrap_admin.py` with deterministic Supabase role/provenance SQL generator (`--user-id|--email`, `--role`, `--actor`) and added unit tests + README/RUNBOOK command docs.

## What Went Wrong
1. Issue: `source_trust_policy` helper test initially failed with asyncpg JSONB binding error (`expected str, got dict`).
- Root cause: test helper passed Python dict directly into `$5::jsonb` instead of serialized JSON.
- Early signal missed: first implementation assumed asyncpg would auto-serialize dict under this query shape.
- Prevention rule: for ad-hoc asyncpg helper inserts into `::jsonb`, serialize payloads explicitly with `json.dumps(...)`.

## What Went Right
1. Improvement: `F2` now has an executable publish policy path tied directly to schema-backed `source_trust_policy`, with auditable decision payloads in provenance.
- Evidence (time/readability/performance/manageability/modularity): policy logic is centralized in repository helpers and no route-level duplication was needed; integration tests codify four policy scenarios.
- Why it worked: existing extract materialization path already had all needed signals (module trust, confidence, risk flags), so policy resolution fit as a local extension.
2. Improvement: role bootstrap moved from placeholder comments to deterministic, parameterized SQL output with automated test coverage.
- Evidence: bootstrap script now has explicit CLI contract and unit tests in fast lane.
- Why it worked: keeping output SQL-only avoids environment coupling while still making provisioning repeatable.

## Reusable Learnings
1. Learning: emit a provenance event whenever policy engines make routing decisions, not just final state transitions.
- Promotion decision: `promote now`
- Promote to: `RUNBOOK.md`
- Why: debugging moderation/publish routing depends on policy explainability and this pattern is reusable across future rule engines.
2. Learning: coverage should include at least one explicit policy override path (`source_key`) in addition to trust-level defaults.
- Promotion decision: `pilot backlog`
- Why: high value for future policy expansion, but broader API-level policy CRUD still pending.

## Receipts
- Commands run:
  - `gh api repos/zakhar-kogan/sloppy-jobulator/branches/main/protection/required_status_checks`
  - `gh api -X PUT repos/zakhar-kogan/sloppy-jobulator/branches/main/protection --input /tmp/branch-protection.json`
  - `uv run --project api --extra dev pytest api/tests --ignore=api/tests/test_discovery_jobs_integration.py`
  - `SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py`
  - `uv run --project api --extra dev ruff check api/app/services/repository.py api/tests/test_discovery_jobs_integration.py api/tests/test_bootstrap_admin_script.py`
  - `uv run --project api --extra dev mypy api/app/services/repository.py`
- Files changed:
  - `api/app/services/repository.py`
  - `api/tests/test_discovery_jobs_integration.py`
  - `api/tests/test_bootstrap_admin_script.py`
  - `scripts/bootstrap_admin.py`
  - `README.md`
  - `.agent/RUNBOOK.md`
  - `docs/roadmap/IMPLEMENTATION_PLAN_v1.2.md`
  - `.agent/CONTINUITY.md`
  - `.agent/execplans/active/EP-2026-02-08__bootstrap-foundation-v1.md`
  - `.agent/notes/2026-02-09_a3-f2-bootstrap-policy.md`
- Tests/checks:
  - API fast tests passed (`13/13`).
  - API DB-backed integration tests passed (`17/17`).
  - Ruff check passed on touched API files.
  - Mypy passed on touched repository module.
