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

## Anti-patterns
1. Hidden side effects without tests or receipts.
2. Swallowing errors or relying on silent fallbacks.
3. Tight coupling across unrelated modules.
4. Large refactors mixed with behavior changes in one diff.
5. Promoting one-off troubleshooting notes into durable docs without repeated evidence.
6. Leaving contradictory guidance across `.agent/*.md` files.
7. Mixing process instructions and app/runtime behavior prompts in one file.
8. Keeping repeated failure knowledge only in chat instead of indexed helper docs.
