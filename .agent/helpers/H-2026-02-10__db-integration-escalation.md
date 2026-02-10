# Helper: H-2026-02-10__db-integration-escalation

## Metadata
- Status: `ACTIVE`
- Scope: Local DB-backed pytest runs from sandboxed Codex sessions.
- Created: `2026-02-10`
- Updated: `2026-02-10`

## Trigger Signals
1. DB integration tests fail with socket permission errors during asyncpg connect.
2. `uv run` in sandbox fails to access default cache path under `$HOME/.cache/uv`.

## Failure Pattern
- Symptom: pytest errors at fixture setup with `PermissionError: [Errno 1] Operation not permitted` while connecting to `localhost:5432`, or `uv` cache permission denial.
- Root cause: sandbox blocks localhost socket/network access and home-directory cache access.
- Early signal missed: first DB-backed run was attempted without escalation and without `UV_CACHE_DIR` override.

## Playbook
1. Use `UV_CACHE_DIR=/tmp/uv-cache` for all `uv run` DB-backed commands.
2. If asyncpg/localhost access fails in sandbox, rerun the same command with escalated permissions.
3. Keep DB lifecycle deterministic: `make db-up -> make db-reset -> test command -> make db-down`.

## Guardrails
1. Run only narrowly scoped test selectors first (`-k "<new tests>"`) before broader integration suites.
2. Keep connection/env args explicit (`SJ_DATABASE_URL` and `DATABASE_URL`) to avoid accidental cross-env writes.

## Verification
1. Command/check: `UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest ...`
- Expected result: selected integration tests pass; no socket permission or uv cache permission errors.

## Promotion Notes
- Promote to `RUNBOOK.md` or `PATTERNS.md` after repeated successful use.

## Revision Log
- `2026-02-10`: initial entry.
- `2026-02-10`: validated again while running F2 trust-policy mixed-trust/validation regression selectors (`8/8`) with sandbox fallback to escalated localhost access.
