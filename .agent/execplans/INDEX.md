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
- `EP-2026-02-08__bootstrap-foundation-v1` — `Status:ACTIVE` — `Created:2026-02-08` — `Updated:2026-02-11` — `Path:.agent/execplans/active/EP-2026-02-08__bootstrap-foundation-v1.md` — `Owner:Codex` — `Summary:Bootstrap runnable API/web/worker/db foundation and harden with DB-backed auth/persistence, CI gates, trust-policy controls, and cockpit/live-E2E operator guardrails.`

## Archived ExecPlans
- `EP-2026-02-10__g2-freshness-automation` — `Status:ARCHIVED` — `Created:2026-02-10` — `Updated:2026-02-10` — `Archived:2026-02-10` — `Path:.agent/execplans/archive/EP-2026-02-10__g2-freshness-automation.md` — `Owner:Codex` — `Summary:Implemented freshness enqueue automation and machine-driven posting downgrade/archive transitions.` — `Outcome:G2 freshness scheduler + transition baseline shipped with DB-backed tests.`
- `EP-2026-02-10__f3-posting-lifecycle` — `Status:ARCHIVED` — `Created:2026-02-10` — `Updated:2026-02-10` — `Archived:2026-02-10` — `Path:.agent/execplans/archive/EP-2026-02-10__f3-posting-lifecycle.md` — `Owner:Codex` — `Summary:Implemented posting lifecycle mutation endpoint with transition guards and candidate synchronization.` — `Outcome:F3 lifecycle baseline shipped with DB-backed tests.`
