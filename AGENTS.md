# AGENTS

## Session startup
1. Read `/.agent/INDEX.md`.
2. Read `/.agent/CONTINUITY.md` before executing.
3. Review `/.agent/CONTEXT.md` for current architecture and constraints.
4. Follow `/.agent/WORKFLOW.md` for phase gates on substantial tasks.
5. Read `/.agent/helpers/INDEX.md` for reusable failure-handling helpers.

## Modes
1. `template` mode (default in this repository): keep the repo sanitized as a reusable scaffold. Do not record live task state in `CONTINUITY`, `DECISIONS`, `notes/`, `helpers/`, or `execplans/`.
2. `project` mode (for downstream cloned repos): run the full self-improving loop with live task-state capture.
3. Use mode-aware scripts:
- Hygiene: `bash scripts/agent-hygiene-check.sh --mode template|project`
- Weekly review: `bash scripts/agent-weekly-review.sh --mode template|project`

## Core rules
1. Explore first, then implement with small, reviewable diffs.
2. Prefer reversible changes and explicit assumptions.
3. Keep machine-readable contracts stable (APIs, schemas, migrations).
4. Run relevant tests/checks before finalizing and report gaps explicitly.
5. For substantial tasks, complete phases in order: clarify -> plan -> implement -> validate -> capture.
6. Keep `AGENTS.md` process-focused; app/runtime prompting belongs in app-specific prompt files.
7. If a subdirectory adds local constraints, add a local `AGENTS.md` there and keep it consistent with root policy.
8. For common/commodity functionality, evaluate existing libraries before building from scratch.
9. Do not install host-level packages unless explicitly requested by the user.

## End-of-task capture (substantial tasks)
1. Answer both:
- What went wrong, why, and what prevention rule should be added?
- What went right, what measurably improved (time/readability/performance/manageability/modularity), and is it reusable?
2. Triage each item with one decision:
- `promote now` (high-leverage and reusable)
- `pilot backlog` (promising but not proven)
- `keep local` (one-off)
3. Apply captured updates according to active mode in `/.agent/WORKFLOW.md`.

## Planning artifacts (project mode)
1. Store major plans in `/.agent/execplans/active/`.
2. Register every plan in `/.agent/execplans/INDEX.md`.
3. Archive completed plans into `/.agent/execplans/archive/` and update index.
4. For major features/refactors, follow `/.agent/PLANS.md`.

## Research and sourcing
1. When uncertain or working with version-sensitive behavior, verify against primary sources.
2. In `project` mode, record key source-driven decisions in `/.agent/CONTINUITY.md` receipts.

## Project-specific configuration (fill this per repo)
1. Build command: `UNCONFIRMED`
2. Test command: `UNCONFIRMED`
3. Lint command: `UNCONFIRMED`
4. Typecheck command: `UNCONFIRMED`
5. Dev run command: `UNCONFIRMED`
6. Agent hygiene check: `bash scripts/agent-hygiene-check.sh --mode template`
7. Weekly maintenance review: `bash scripts/agent-weekly-review.sh --mode template`
