# ExecPlan Index

Tracks execution plans for this repository.

Mode note:
1. `template` mode keeps this index scaffold-only (`(none yet)` entries).
2. `project` mode tracks live active/archived plans.

## Conventions
1. Active plans: `/.agent/execplans/active/`
2. Archived plans: `/.agent/execplans/archive/`
3. Filename format: `EP-YYYY-MM-DD__slug.md`

## Entry format
- `EP-YYYY-MM-DD__slug` — `Status:<DRAFT|ACTIVE|BLOCKED|DONE|ARCHIVED>` — `Created:YYYY-MM-DD` — `Updated:YYYY-MM-DD` — `Path:<repo-relative path>` — `Owner:<UNCONFIRMED|name>` — `Summary:<one line>` — `Links:<optional>`

For archived plans add:
- `Archived:YYYY-MM-DD` — `Outcome:<one line>`

## Template
- Use `/.agent/execplans/active/EP-TEMPLATE.md` when starting a new plan.

## Active ExecPlans
- `EP-2026-02-08__bootstrap-foundation-v1` — `Status:ACTIVE` — `Created:2026-02-08` — `Updated:2026-02-08` — `Path:.agent/execplans/active/EP-2026-02-08__bootstrap-foundation-v1.md` — `Owner:Codex` — `Summary:Bootstrap runnable API/web/worker/db foundation and harden with DB-backed auth/persistence + CI gates.`

## Archived ExecPlans
- (none yet)
