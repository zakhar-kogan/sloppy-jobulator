# L1 E2E PR Summary (2026-02-11)

## Scope Included In This PR
1. Live cockpit negative/authz browser coverage (`401`, `403`, `422`, merge-conflict path).
2. Live persistence assertions for cockpit actions (candidate events, module mutation timestamps, jobs enqueue/reap transitions).
3. `web-e2e-live` CI runtime hardening (uv/pnpm/Playwright caching, timeout budgets, scoped retry-once behavior).
4. Admin proxy failure-mapping API contract tests (backend `4xx/5xx` passthrough, bounds pass-through, non-JSON error-body stability).

## Test Matrix (Tight)

| Layer | Command | Focus | Result |
|---|---|---|---|
| Web contracts | `fnm exec --using 24.13.0 pnpm --dir web test:contracts` | Cockpit query/path contracts + admin proxy failure mapping (`422` bounds, `503`, non-JSON `{detail}`, config fail-fast) | pass (`13/13`) |
| Web typecheck | `fnm exec --using 24.13.0 pnpm --dir web typecheck` | Type integrity for new proxy-core and tests | pass |
| Live browser E2E | `(escalated) UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... fnm exec --using 24.13.0 pnpm --dir web test:e2e:live` | Real API/DB moderation/operator flows + negative/authz + persistence assertions | pass (`3/3`) |
| Agent contract | `bash scripts/agent-hygiene-check.sh --mode project` | Agent policy/workflow hygiene | pass |

## CI Matrix Impact

| Job | Change | Why |
|---|---|---|
| `web-e2e-live` | Added `uv` cache and `uv sync --project api --extra dev --frozen` | Deterministic API dependency install and faster reruns |
| `web-e2e-live` | Added pnpm dependency cache via `actions/setup-node` | Reduces install latency/flake risk |
| `web-e2e-live` | Added Playwright browser cache + explicit Chromium install | Stabilizes browser availability and startup time |
| `web-e2e-live` | Added job/step timeout budgets + scoped retry-once wrapper only for live E2E step | Limits runaway runtime while tolerating transient startup failures |
| `web/playwright.live.config.ts` | Removed blanket CI per-test retry, added global CI timeout, switched to cached Chromium path | Keeps retry policy explicit at CI-step level and runtime bounded |

## Known Risks (For Reviewer Signoff)
1. Live E2E still depends on local multi-process startup (`mock_supabase_auth` + API + Next dev server) inside one job.
- Mitigation: scoped retry-once + explicit webServer timeouts + bounded job timeout.
2. Admin proxy failure-mapping tests exercise shared forwarding core (`admin-api-core`) rather than importing Next route handlers in `node:test`.
- Mitigation: route wrappers are thin and live E2E (`/api/admin/*`) passes end-to-end after refactor.
3. Auth in live E2E uses mock Supabase user endpoint; production Supabase URL/key and role metadata conventions remain environment-dependent.
- Mitigation: retain this as explicit open question in continuity and require staging verification before release.
4. Freshness enqueue count is data-dependent in shared DB state.
- Mitigation: tests assert queue delta equals returned enqueue count, not a fixed absolute count.

## Recommendation
Proceed to L1 full E2E scope expansion with this PR as baseline. Remaining work should focus on additional moderation/admin scenario breadth rather than runtime plumbing.
