# Agent Index

Start here each session.

## Core files
1. `/.agent/CONTINUITY.md` - compact state that survives session/context loss.
2. `/.agent/CONTEXT.md` - architecture and constraints snapshot.
3. `/.agent/WORKFLOW.md` - phase-gated task execution policy.
4. `/.agent/PLANS.md` - ExecPlan requirements and lifecycle.
5. `/.agent/RUNBOOK.md` - operational procedures and commands.
6. `/.agent/PATTERNS.md` - proven patterns and anti-patterns.
7. `/.agent/DECISIONS.md` - ADR-lite log.
8. `/.agent/PROMPTS.md` - reusable operator prompts.

## Planning files
1. `/.agent/execplans/INDEX.md` - registry of active/archived execution plans.
2. `/.agent/execplans/active/` - active plans.
3. `/.agent/execplans/archive/` - completed plans.
4. `/.agent/execplans/active/EP-TEMPLATE.md` - template for new plans.

## Note template
1. `/.agent/notes/TEMPLATE.md` - template for per-task notes.

## Helper memory
1. `/.agent/helpers/INDEX.md` - index of reusable failure/workflow helpers.
2. `/.agent/helpers/TEMPLATE.md` - template for new helper docs.

## Maintenance tools
1. `/scripts/agent-hygiene-check.sh` - validates core agentic starter contract.
2. `/scripts/agent-weekly-review.sh` - weekly maintenance helper.

## Workflow
1. Read `CONTINUITY.md`, then `CONTEXT.md`, then `WORKFLOW.md`, then `helpers/INDEX.md`.
2. Execute task.
3. Select workflow mode (`template` for this repo, `project` for downstream repos).
4. Run balanced capture (`went wrong + prevention`, `went right + measurable improvement`).
5. Apply updates according to mode in `WORKFLOW.md`.
