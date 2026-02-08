# ExecPlan Rules

Use ExecPlans for major features, multi-step refactors, migrations, or work that spans multiple sessions.

Mode note:
1. In `template` mode, keep plan folders/index scaffolded and empty.
2. In `project` mode, create and maintain live plans.

## Storage and Lifecycle
1. Active plans live in `/.agent/execplans/active/`.
2. Archived plans live in `/.agent/execplans/archive/`.
3. Every plan must be listed in `/.agent/execplans/INDEX.md`.
4. Never delete plans; archive them.

## Naming
1. Filename format: `EP-YYYY-MM-DD__slug.md`.
2. Keep slug short, stable, and kebab-case.

## Required Plan Header
Each plan file must begin with:
1. Plan ID: `EP-YYYY-MM-DD__slug`
2. Status: `DRAFT | ACTIVE | BLOCKED | DONE | ARCHIVED`
3. Created: `YYYY-MM-DD`
4. Last Updated: `YYYY-MM-DD`
5. Owner: `UNCONFIRMED | <name>`

## Required Sections
1. Purpose / Big Picture
2. Scope and Constraints
3. Progress (checkbox list, updated as work proceeds)
4. Decision Log (what changed, why, date)
5. Plan of Work (concrete steps and touched paths)
6. Validation and Acceptance (commands + expected outcomes)
7. Idempotence and Recovery
8. Outcomes and Retrospective

## Plan Quality Bar
1. Self-contained: a new contributor can execute with only repo + plan file.
2. Outcome-focused: defines observable behavior, not only code edits.
3. Verifiable: includes explicit commands and pass/fail expectations.
4. Maintained: progress and decisions are updated as execution evolves.

## Index Maintenance
1. Add new plans under `Active ExecPlans`.
2. When complete: set `Status:DONE`, move file to archive, then set `Status:ARCHIVED`.
3. Move index entry to `Archived ExecPlans` and include one-line outcome.
