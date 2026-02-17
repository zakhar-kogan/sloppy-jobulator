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
- `EP-2026-02-11__j1-j2-m1-observability-safety` — `Status:ACTIVE` — `Created:2026-02-11` — `Updated:2026-02-11` — `Path:.agent/execplans/active/EP-2026-02-11__j1-j2-m1-observability-safety.md` — `Owner:Codex` — `Summary:Implement J1 OTel instrumentation, J2 dashboards/SLO alerts, and remaining M1 deploy+migration safety gates.`
- `EP-2026-02-12__env-bindings-e2-h2l1` — `Status:ACTIVE` — `Created:2026-02-12` — `Updated:2026-02-15` — `Path:.agent/execplans/active/EP-2026-02-12__env-bindings-e2-h2l1.md` — `Owner:Codex` — `Summary:Wire env-bound observability/deploy baseline and ship incremental E2 redirect semantics plus H2/L1 cockpit breadth expansions.`

- `EP-2026-02-16__completion-checklist-p0-launch` — `Status:ACTIVE` — `Created:2026-02-16` — `Updated:2026-02-16` — `Path:.agent/execplans/active/EP-2026-02-16__completion-checklist-p0-launch.md` — `Owner:Codex` — `Summary:Checklist-driven closure of remaining launch-critical in-progress work (`G1`, `F2`, `L1`, `J1`, `J2`, `M1`) with strict validation receipts.`
- `EP-2026-02-16__80-20-descope-simplification` — `Status:ACTIVE` — `Created:2026-02-16` — `Updated:2026-02-16` — `Path:.agent/execplans/active/EP-2026-02-16__80-20-descope-simplification.md` — `Owner:Codex` — `Summary:Stage-wise simplification plan to align implementation complexity with the 4-core product surfaces and avoid enterprise-pattern overreach.`

## Archived ExecPlans
- `EP-2026-02-15__e1-domain-overrides-productization` — `Status:ARCHIVED` — `Created:2026-02-15` — `Updated:2026-02-15` — `Archived:2026-02-15` — `Path:.agent/execplans/archive/EP-2026-02-15__e1-domain-overrides-productization.md` — `Owner:Codex` — `Summary:Complete E1 persisted per-domain normalization override contract across admin API/UI, ingest, redirect worker path, and DB-backed tests.` — `Outcome:E1 per-domain override contract completed and validated with DB-backed + live admin E2E coverage.`
- `EP-2026-02-10__g2-freshness-automation` — `Status:ARCHIVED` — `Created:2026-02-10` — `Updated:2026-02-10` — `Archived:2026-02-10` — `Path:.agent/execplans/archive/EP-2026-02-10__g2-freshness-automation.md` — `Owner:Codex` — `Summary:Implemented freshness enqueue automation and machine-driven posting downgrade/archive transitions.` — `Outcome:G2 freshness scheduler + transition baseline shipped with DB-backed tests.`
- `EP-2026-02-10__f3-posting-lifecycle` — `Status:ARCHIVED` — `Created:2026-02-10` — `Updated:2026-02-10` — `Archived:2026-02-10` — `Path:.agent/execplans/archive/EP-2026-02-10__f3-posting-lifecycle.md` — `Owner:Codex` — `Summary:Implemented posting lifecycle mutation endpoint with transition guards and candidate synchronization.` — `Outcome:F3 lifecycle baseline shipped with DB-backed tests.`
- `EP-2026-02-16__h2-queue-facets-quick-filters` — `Status:ARCHIVED` — `Created:2026-02-16` — `Updated:2026-02-16` — `Archived:2026-02-16` — `Path:.agent/execplans/archive/EP-2026-02-16__h2-queue-facets-quick-filters.md` — `Owner:Codex` — `Summary:Add candidate queue facets/counts (state/source/age) and one-click cockpit quick filter chips to reduce moderation triage time.` — `Outcome:H2 queue facets endpoint, cockpit quick chips, and targeted API/web validations completed.`
- `EP-2026-02-17__ci-stabilization-main-green` — `Status:ARCHIVED` — `Created:2026-02-17` — `Updated:2026-02-17` — `Archived:2026-02-17` — `Path:.agent/execplans/archive/EP-2026-02-17__ci-stabilization-main-green.md` — `Owner:Codex` — `Summary:Restore green CI on main by fixing trust-policy integration validation drift and live cockpit E2E expectation drift/flakes.` — `Outcome:CI run 22110713985 completed green after trust-policy validator compatibility restoration and live cockpit E2E expectation hardening.`
