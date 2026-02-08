# Task Note: 2026-02-08 db-auth-ci-hardening

## Task
- Request: proceed with Postgres repositories, real machine/human auth validation, CI workflow gates, and relocate handoff docs so `handoff/` can be removed.
- Scope: API persistence/auth hardening, worker credential alignment, CI automation, docs path normalization.
- Constraints: reviewable diffs, no host-level installs, report validation gaps explicitly.

## Actions Taken
1. Added `api/app/services/repository.py` and replaced in-memory route handling for discoveries, evidence, jobs, and postings.
2. Implemented machine credential verification against `modules` + active `module_credentials` and Supabase-backed human token verification in `api/app/core/security.py`.
3. Added dev module and credential seed records in `db/seeds/001_taxonomy.sql` and aligned worker default API key.
4. Added `.github/workflows/ci.yml` for api/workers/web lint/typecheck/tests gates.
5. Moved handoff artifacts to `docs/spec/` and `docs/roadmap/`, updated references, and removed `handoff/`.

## What Went Wrong
1. Issue: project hygiene check failed after doc migration.
- Root cause: absolute source paths remained in `docs/TRANSFER_README.md`.
- Early signal missed: no immediate absolute-path grep before running hygiene checks.
- Prevention rule: run `rg -n "/Users/" AGENTS.md .agent docs .github` after large doc moves.

## What Went Right
1. Improvement: API contract behavior now matches schema-backed durability and credential controls.
- Evidence (manageability/modularity): all mutation endpoints call one repository abstraction with explicit conflict/not-found/forbidden semantics.
- Why it worked: route/controller logic stayed thin while DB semantics were centralized.
2. Improvement: CI now enforces multi-service quality gates on every push/PR.
- Evidence (manageability): lint/typecheck/tests are codified for `api`, `workers`, and `web` in one workflow.
- Why it worked: per-service jobs isolate failures and match existing make targets.

## Reusable Learnings
1. Learning: centralizing DB transition rules behind repository error types keeps HTTP handlers deterministic and easier to evolve.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `PATTERNS.md`
- Why: applies broadly to all future API entities and avoids duplicated state-machine checks.
2. Learning: after migration from transfer docs to canonical docs, immediately run absolute-path hygiene grep.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `RUNBOOK.md`
- Why: catches recurring copy/move residue before CI.

## Receipts
- Commands run:
- `python -m compileall api/app workers/app`
- `uv venv .venv`
- `uv pip install -e './api[dev]' -e './workers[dev]'`
- `fnm use 24.13.0 && pnpm install --dir web`
- `make lint`
- `make typecheck`
- `make test`
- `make build`
- `bash scripts/agent-hygiene-check.sh --mode project`
- Files changed:
- API routes/security/config/repository, DB seed/schema metadata refs, CI workflow, docs relocation, `.agent` capture files.
- Tests/checks:
- lint/typecheck/tests/build and hygiene checks all succeeded after local toolchain install.
