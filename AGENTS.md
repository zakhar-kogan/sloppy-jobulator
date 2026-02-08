# AGENTS

## Session startup
1. Read `/.agent/INDEX.md`.
2. Read `/.agent/CONTINUITY.md` before executing.
3. Review `/.agent/CONTEXT.md` for current architecture and constraints.
4. Follow `/.agent/WORKFLOW.md` for phase gates on substantial tasks.
5. Read `/.agent/helpers/INDEX.md` for reusable failure-handling helpers.

## Modes
1. `template` mode (default in template repos): keep the repo sanitized as a reusable scaffold. Do not record live task state in `CONTINUITY`, `DECISIONS`, `notes/`, `helpers/`, or `execplans/`.
2. `project` mode (active for this repository): run the full self-improving loop with live task-state capture.
3. Use mode-aware scripts:
- Hygiene: `bash scripts/agent-hygiene-check.sh --mode template|project`
- Weekly review: `bash scripts/agent-weekly-review.sh --mode template|project`

## Core rules
1. Explore first, then implement with small, reviewable diffs.
2. Prefer reversible changes and explicit assumptions.
3. Keep machine-readable contracts stable (APIs, schemas, migrations).
4. Run relevant tests/checks before finalizing and report gaps explicitly.
5. For substantial tasks, complete phases in order: clarify -> plan -> implement -> validate -> capture.
6. Keep `AGENTS.md` process-focused; app/runtime prompting belongs in app-specific prompt files.
7. If a subdirectory adds local constraints, add a local `AGENTS.md` there and keep it consistent with root policy.
8. For common/commodity functionality, evaluate existing libraries before building from scratch.
9. Do not install host-level packages unless explicitly requested by the user.

## End-of-task capture (substantial tasks)
1. Answer both:
- What went wrong, why, and what prevention rule should be added?
- What went right, what measurably improved (time/readability/performance/manageability/modularity), and is it reusable?
2. Triage each item with one decision:
- `promote now` (high-leverage and reusable)
- `pilot backlog` (promising but not proven)
- `keep local` (one-off)
3. Apply captured updates according to active mode in `/.agent/WORKFLOW.md`.

## Planning artifacts (project mode)
1. Store major plans in `/.agent/execplans/active/`.
2. Register every plan in `/.agent/execplans/INDEX.md`.
3. Archive completed plans into `/.agent/execplans/archive/` and update index.
4. For major features/refactors, follow `/.agent/PLANS.md`.

## Research and sourcing
1. When uncertain or working with version-sensitive behavior, verify against primary sources.
2. In `project` mode, record key source-driven decisions in `/.agent/CONTINUITY.md` receipts.

## Project-specific configuration
1. Build command: `make build`
2. Test command: `make test`
3. Lint command: `make lint`
4. Typecheck command: `make typecheck`
5. Dev run command: `make dev`
6. Agent hygiene check: `bash scripts/agent-hygiene-check.sh --mode project`
7. Weekly maintenance review: `bash scripts/agent-weekly-review.sh --mode project`

## Skills
A skill is a set of local instructions to follow that is stored in a `SKILL.md` file. Below is the list of skills that can be used. Each entry includes a name, description, and file path so you can open the source for full instructions when using a specific skill.
### Available skills
- pdf: Use when tasks involve reading, creating, or reviewing PDF files where rendering and layout matter; prefer visual checks by rendering pages (Poppler) and use Python tools such as `reportlab`, `pdfplumber`, and `pypdf` for generation and extraction. (file: `$CODEX_HOME/skills/pdf/SKILL.md`)
- skill-creator: Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Codex's capabilities with specialized knowledge, workflows, or tool integrations. (file: `$CODEX_HOME/skills/.system/skill-creator/SKILL.md`)
- skill-installer: Install Codex skills into `$CODEX_HOME/skills` from a curated list or a GitHub repo path. Use when a user asks to list installable skills, install a curated skill, or install a skill from another repo (including private repos). (file: `$CODEX_HOME/skills/.system/skill-installer/SKILL.md`)
### How to use skills
- Discovery: The list above is the skills available in this session (name + description + file path). Skill bodies live on disk at the listed paths.
- Trigger rules: If the user names a skill (with `$SkillName` or plain text) OR the task clearly matches a skill's description shown above, you must use that skill for that turn. Multiple mentions mean use them all. Do not carry skills across turns unless re-mentioned.
- Missing/blocked: If a named skill isn't in the list or the path can't be read, say so briefly and continue with the best fallback.
- How to use a skill (progressive disclosure):
  1) After deciding to use a skill, open its `SKILL.md`. Read only enough to follow the workflow.
  2) When `SKILL.md` references relative paths (e.g., `scripts/foo.py`), resolve them relative to the skill directory listed above first, and only consider other paths if needed.
  3) If `SKILL.md` points to extra folders such as `references/`, load only the specific files needed for the request; don't bulk-load everything.
  4) If `scripts/` exist, prefer running or patching them instead of retyping large code blocks.
  5) If `assets/` or templates exist, reuse them instead of recreating from scratch.
- Coordination and sequencing:
  - If multiple skills apply, choose the minimal set that covers the request and state the order you'll use them.
  - Announce which skill(s) you're using and why (one short line). If you skip an obvious skill, say why.
- Context hygiene:
  - Keep context small: summarize long sections instead of pasting them; only load extra files when needed.
  - Avoid deep reference-chasing: prefer opening only files directly linked from `SKILL.md` unless you're blocked.
  - When variants exist (frameworks, providers, domains), pick only the relevant reference file(s) and note that choice.
- Safety and fallback: If a skill can't be applied cleanly (missing files, unclear instructions), state the issue, pick the next-best approach, and continue.
