# H-2026-02-12__async-resource-loop-lifecycle

- Status: `ACTIVE`
- Scope: Async tests using pooled resources (for example `asyncpg.Pool`)
- Trigger: Event-loop-closed errors during teardown after creating resource pools in one `asyncio.run(...)` call and closing in another.

## Problem
Splitting pool creation/use and close across separate `asyncio.run(...)` calls can bind teardown to a closed loop and raise runtime errors.

## Playbook
1. Keep resource lifecycle in one coroutine:
- create/use/close inside a single async function.
2. Call `asyncio.run(...)` once for that end-to-end coroutine.
3. For DB-backed integration in Codex sandbox, pair with escalation helper when localhost access is denied.

## Verification
1. Re-run failing test and confirm teardown no longer raises `RuntimeError: Event loop is closed`.
2. Ensure test assertions still pass and no pool warnings remain.
