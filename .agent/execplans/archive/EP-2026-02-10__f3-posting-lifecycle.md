# ExecPlan: EP-2026-02-10__f3-posting-lifecycle

## Metadata
- Status: `ARCHIVED`
- Created: `2026-02-10`
- Updated: `2026-02-10`
- Owner: `Codex`

## Purpose / Big Picture
Advance roadmap item `F3` by implementing explicit posting lifecycle transitions (`active/stale/archived/closed`) with deterministic candidate-state synchronization and auditable provenance.

## Scope and Constraints
- In scope:
1. Add moderated posting lifecycle mutation endpoint.
2. Enforce lifecycle transition rules and downgrade/reopen semantics.
3. Add integration coverage for valid and invalid transitions.
- Out of scope:
1. Scheduled freshness execution and retry workflows (`G2`).
2. New worker job kinds or schedulers.
- Constraints:
1. Preserve existing `GET /postings` contracts and current moderation candidate flows.
2. Keep schema unchanged; implement at API/repository level.
3. Capture all state mutations with provenance events.

## Progress (checkbox list, updated as work proceeds)
- [x] Add `PATCH /postings/{id}` schema/route with human moderation authorization.
- [x] Implement repository posting-status transition + candidate-state synchronization.
- [x] Add integration tests for lifecycle transitions and invalid conflicts.
- [x] Run targeted integration tests for posting lifecycle paths.
- [x] Record outcomes/receipts in project-mode capture files.

## Decision Log (what changed, why, date)
- 2026-02-10: Chose explicit posting-level lifecycle mutation (instead of only candidate-level mutations) to satisfy spec admin/moderation contract and expose `stale` transitions not representable as candidate state.
- 2026-02-10: Enforced deterministic candidate synchronization mapping (`active|stale -> published`, `archived -> archived`, `closed -> closed`) with transition guards to prevent illegal reopen paths.

## Plan of Work (concrete steps and touched paths)
1. API contract and route wiring.
- Paths: `api/app/schemas/postings.py`, `api/app/api/routes/postings.py`.
2. Repository implementation and transition validation.
- Paths: `api/app/services/repository.py`.
3. Integration test additions.
- Paths: `api/tests/test_discovery_jobs_integration.py`.
4. Project-mode capture updates.
- Paths: `.agent/notes/*`, `.agent/CONTINUITY.md`, `.agent/execplans/INDEX.md`, this plan file.

## Validation and Acceptance (commands + expected outcomes)
1. `SJ_DATABASE_URL=... DATABASE_URL=... uv run --project api --extra dev pytest api/tests/test_discovery_jobs_integration.py -k "posting_lifecycle or moderation_candidate_state_transitions_update_posting_status"`
- Expected: posting lifecycle tests pass with deterministic status/state transitions.
2. `uv run --project api --extra dev pytest api/tests --ignore=api/tests/test_discovery_jobs_integration.py`
- Expected: non-integration API tests remain green.

## Idempotence and Recovery
1. New endpoint is additive and backward-compatible with existing read contracts.
2. Transition guards prevent illegal state moves; override route remains escape hatch for moderators.
3. If regressions appear, rollback is limited to API/repository route additions without schema rollback.

## Outcomes and Retrospective
- Outcome: `DONE`
- Follow-ups:
1. Implement `G2` freshness checker job scheduling and automatic `active -> stale -> archived` transitions.
