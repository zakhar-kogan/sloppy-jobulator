# Task Note: H2 admin trust-policy UI wiring

## Task
- Request: Wire admin UI flows to `/admin/source-trust-policy` (list/upsert/enable toggle) if this is next in plan.
- Scope: Next.js `web/` only, preserving existing API contracts.
- Constraints: Reuse existing FastAPI admin endpoints; keep diffs reviewable; validate with web lint/typecheck/build.

## Actions Taken
1. Confirmed from `docs/roadmap/IMPLEMENTATION_PLAN_v1.2.md` and active execplan that `H2` trust-policy UI wiring is next.
2. Added Next.js server proxy routes for list/upsert/toggle: `web/app/api/admin/source-trust-policy/**`.
3. Added admin UI screen at `web/app/admin/source-trust-policy` with filterable list, upsert form (`rules_json` editor), and row-level enable toggle.
4. Added typed contract helpers in `web/lib/source-trust-policy.ts` and shared proxy helper in `web/lib/admin-source-trust-policy-api.ts`.
5. Updated navigation/style and project-mode capture docs.
6. Ran `pnpm --dir web lint`, `pnpm --dir web typecheck`, and `pnpm --dir web build`.

## What Went Wrong
1. Issue: UI depends on web-process env vars and fails if they are missing.
- Root cause: Admin bearer auth is server-side, so proxy routes require runtime config.
- Early signal missed: none; discovered while defining request wiring.
- Prevention rule: Keep proxy configuration errors explicit and document required env vars in runbook.

## What Went Right
1. Improvement: Proxy pattern kept bearer token server-side while allowing client-side admin UX.
- Evidence (time/readability/performance/manageability/modularity): No auth token handling added to browser code; one reusable proxy helper serves all three methods.
- Why it worked: Next.js route handlers cleanly separate secure upstream calls from client state/render logic.

## Reusable Learnings
1. Learning: For admin browser flows with privileged upstream auth, prefer Next.js server proxy handlers over direct client calls.
- Promotion decision: `promote now`
- Promote to (if `promote now`): `RUNBOOK.md`
- Why: Env requirements and path conventions are operationally important for local/dev/prod parity.

## Receipts
- Commands run:
  - `pnpm --dir web lint`
  - `pnpm --dir web typecheck`
  - `pnpm --dir web build`
- Files changed:
  - `web/app/admin/source-trust-policy/page.tsx`
  - `web/app/admin/source-trust-policy/source-trust-policy-admin.tsx`
  - `web/app/api/admin/source-trust-policy/route.ts`
  - `web/app/api/admin/source-trust-policy/[sourceKey]/route.ts`
  - `web/lib/admin-source-trust-policy-api.ts`
  - `web/lib/source-trust-policy.ts`
  - `web/app/page.tsx`
  - `web/app/globals.css`
  - `.agent/CONTINUITY.md`
  - `.agent/execplans/active/EP-2026-02-08__bootstrap-foundation-v1.md`
  - `docs/roadmap/IMPLEMENTATION_PLAN_v1.2.md`
  - `.agent/RUNBOOK.md`
- Tests/checks:
  - `pnpm --dir web lint` (pass)
  - `pnpm --dir web typecheck` (pass)
  - `pnpm --dir web build` (pass)
