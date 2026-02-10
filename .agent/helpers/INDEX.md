# Helper Index

Machine-facing helper memory for recurring failures and repeatable workflows.

## Usage
1. Read this index at task startup.
2. Reuse existing helpers when triggers match.
3. After a failure review, update an existing helper or add a new one.
4. Keep entries short and operational; promote stable guidance into `RUNBOOK.md` or `PATTERNS.md`.

## Entry format
- `H-YYYY-MM-DD__slug` — `Status:<ACTIVE|STABLE|RETIRED>` — `Path:<repo-relative path>` — `Scope:<where it applies>` — `Summary:<one line>`

## Active Helpers
- `H-2026-02-10__db-integration-escalation` — `Status:ACTIVE` — `Path:.agent/helpers/H-2026-02-10__db-integration-escalation.md` — `Scope:Local DB-backed pytest runs from sandboxed Codex sessions` — `Summary:Use /tmp uv cache + escalation fallback when sandbox blocks localhost Postgres access.`

## Stable Helpers
- (none yet)

## Retired Helpers
- (none yet)
