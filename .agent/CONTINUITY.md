# Continuity Ledger

Facts only. No transcripts. If unknown, write `UNCONFIRMED`.
Each entry must include date and provenance tag: `[USER]`, `[CODE]`, `[TOOL]`, `[ASSUMPTION]`.
In `project` mode, update this file whenever Goal/Now/Next/Decisions materially change.
In `template` mode, keep this file as scaffold-only.

## Size caps
- Snapshot: <= 25 non-empty lines.
- Done (recent): <= 7 bullets.
- Working set: <= 12 bullets.
- Receipts: <= 20 bullets (keep recent, compress older items).

## Snapshot

Goal: Ship Phase 1 baseline with DB-backed API persistence/auth, worker compatibility, and CI quality gates.
Now: `F2` repository trust-policy writes now enforce strict `rules_json` merge-routing validation (allowed actions, route-label format, unknown-key rejection), and integration coverage includes mixed trust + conflicting dedupe scenarios.
Next: Add admin policy-management endpoints that call the validated repository write path and add API-level contract tests for validation failures/success paths.
Open Questions: exact production Supabase URL/key provisioning and human role metadata conventions are UNCONFIRMED.

## Done (recent)
- 2026-02-10 `[CODE]` Added strict repository validation for `source_trust_policy.rules_json` merge-routing contracts (top-level key whitelist, decision-map unknown-key rejection, action whitelist, route-label format checks).
- 2026-02-10 `[CODE]` Added repository write API `upsert_source_trust_policy(...)` and enforced strict validation before DB persistence.
- 2026-02-10 `[CODE]` Switched integration test policy upsert helper to use repository write path so trust-policy writes now run through validation logic.
- 2026-02-10 `[CODE]` Expanded integration regression coverage with mixed-trust dedupe cases: semi-trusted conflicting hash routing to review and untrusted rejected merge routing behavior.
- 2026-02-10 `[CODE]` Added integration negative tests for invalid trust-policy writes (`unknown decision key`, invalid merge action, invalid moderation route label).
- 2026-02-10 `[CODE]` Updated roadmap `F2` status and next steps to document strict merge-routing validation and explicit pending admin policy API contract targets.

## Working set
- 2026-02-08 `[ASSUMPTION]` Target stack remains Next.js + FastAPI + Supabase + Cloud Run per spec.
- 2026-02-08 `[CODE]` Node toolchain standardized on `fnm` + `pnpm` with root `.node-version` and `web/pnpm-lock.yaml`.
- 2026-02-08 `[CODE]` Local API `make test` keeps integration tests skipped unless DB URL env vars are set (while `make test-integration` enforces DB-backed run).

## Decisions
- 2026-02-08 `[CODE]` D-001 through D-004 active in `.agent/DECISIONS.md`.

## Receipts
- 2026-02-10 `[TOOL]` `uv run --project api --extra dev ruff check api/app/services/repository.py api/tests/test_discovery_jobs_integration.py` passed.
- 2026-02-10 `[TOOL]` `uv run --project api --extra dev mypy api/app/services/repository.py` passed.
- 2026-02-10 `[TOOL]` `make db-up -> make db-reset -> (escalated) UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "mixed_trust or write_rejects_unknown_merge_routing_key or write_rejects_invalid_merge_action or write_rejects_invalid_route_label or trust_policy_can_override_needs_review_merge_route_for_source or trust_policy_can_override_rejected_merge_route_for_source or trust_policy_override_applies_when_auto_merge_fallbacks_to_needs_review" -> make db-down` passed (`8/8` selected).
- 2026-02-10 `[TOOL]` `bash scripts/agent-hygiene-check.sh --mode project` passed.
