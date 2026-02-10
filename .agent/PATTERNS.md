# Patterns

## Good patterns
1. Small, reversible changes with explicit validation.
2. Contract-first changes for APIs/schemas.
3. Idempotent jobs and retries with bounded backoff.
4. Observability baked into new flows (logs/metrics/traces).
5. Separate transient task notes (`notes/`) from durable policy docs (`RUNBOOK`, `PATTERNS`, `DECISIONS`).
6. Keep continuity entries date-stamped with provenance tags for compaction-safe handoff.
7. Keep agent instruction layers scoped: root policy in root `AGENTS.md`, local constraints in local `AGENTS.md`.
8. Enforce framework integrity with lightweight scripted checks and CI.
9. Maintain compact machine-facing helper docs and an index for recurring failures.
10. Keep API route handlers thin by centralizing DB transition/idempotency logic in repository methods with explicit error mapping.
11. For DB-dependent integration tests, allow local skip when DB URL is absent and enforce full coverage through CI-provisioned database services.
12. Gate projection/publish-side writes on explicit payload signals plus required-field completeness to prevent accidental public entity creation from stub processor outputs.
13. Keep retry/dead-letter resolution in one server-side transition path (using persisted attempt counts) so all workers share consistent failure semantics.
14. For Supabase-backed human authz, trust elevated roles only from operator-controlled claim sources (e.g., `app_metadata`), not user-editable profile metadata.
15. Keep moderation state-transition rules and posting lifecycle coupling in one transactional repository path to avoid route-level policy drift.
16. For multi-entity lifecycle domains, define explicit transition guards per entity and enforce deterministic cross-entity mapping in the same transaction (e.g., posting status to candidate state).
17. For new durable job kinds, branch behavior in one `submit_job_result` transaction path so retries/dead-letter semantics stay centralized and consistent across workers.
18. When reading dynamic JSON payloads in typed worker code, normalize to typed locals first (`raw_payload` -> `dict[str, Any]`) before field access to keep mypy stable.

## Anti-patterns
1. Hidden side effects without tests or receipts.
2. Swallowing errors or relying on silent fallbacks.
3. Tight coupling across unrelated modules.
4. Large refactors mixed with behavior changes in one diff.
5. Promoting one-off troubleshooting notes into durable docs without repeated evidence.
6. Leaving contradictory guidance across `.agent/*.md` files.
7. Mixing process instructions and app/runtime behavior prompts in one file.
8. Keeping repeated failure knowledge only in chat instead of indexed helper docs.
