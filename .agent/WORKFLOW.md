# Agent Workflow

Use this for substantial tasks. Keep phases ordered.

## Modes
1. `template` mode: keep this repository sanitized as a template baseline.
2. `project` mode: use full live task-state capture in downstream repos.
3. Scripts accept mode flags:
- `bash scripts/agent-hygiene-check.sh --mode template|project`
- `bash scripts/agent-weekly-review.sh --mode template|project`

## Phase 1: Clarify
1. Restate request, scope, and constraints.
2. Mark unknowns as `UNCONFIRMED` instead of guessing.
3. Check `/.agent/helpers/INDEX.md` for relevant helper patterns.

Exit criteria:
1. Task objective is explicit.
2. Assumptions are listed.

## Phase 2: Plan
1. Create a short execution plan in `/.agent/execplans/active/` for major work.
2. Structure major plans according to `/.agent/PLANS.md`.
3. Define validation steps and rollback-safe sequencing.

Exit criteria:
1. Plan steps are concrete and testable.
2. Risks and mitigations are documented.

## Phase 3: Implement
1. Apply small, reviewable diffs.
2. Keep contracts stable unless explicitly changing them.
3. Record important commands/files in task notes.

Exit criteria:
1. Changes are complete for scoped objective.
2. Diff size stays reviewable.

## Phase 4: Validate
1. Run relevant checks (build/test/lint/typecheck) if commands are known.
2. If a command is `UNCONFIRMED` or unavailable, report the gap explicitly.

Exit criteria:
1. Validation evidence is captured.
2. Remaining risk is stated.

## Phase 5: Capture
1. Run a balanced review:
- What went wrong, why, and prevention?
- What went right, what measurably improved, and is it reusable?
2. Triage each item:
- `promote now` (high-leverage and reusable)
- `pilot backlog` (promising but unproven)
- `keep local` (one-off context)
3. In `project` mode:
- Add/update notes in `/.agent/notes/` (including pilot backlog items).
- Promote `promote now` items into `RUNBOOK`, `PATTERNS`, or `DECISIONS`.
- Update helpers in `/.agent/helpers/` for repeatable failure/workflow playbooks.
- In `project` mode, update `CONTINUITY` with Goal/Now/Next plus receipts.
4. In `template` mode:
- Do not add live task-state entries to `CONTINUITY`, `DECISIONS`, `notes/`, `helpers/`, or `execplans/`.
- Apply only scaffold/policy/template improvements.

Exit criteria:
1. Reusable learning is persisted.
2. Chosen mode constraints are respected.
3. Promotion decisions are explicit (`promote now | pilot backlog | keep local`).
