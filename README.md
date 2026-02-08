# tmpl-starter

Template for an extremely simple but effective agent workflow with:
- a stable `/.agent` contract
- phase-gated execution for substantial tasks
- mode-aware hygiene checks (`template` vs `project`)

## Repository Mode

This repository is maintained in `template` mode.

- `template` mode: scaffold stays sanitized (no live task-state writes in continuity/decisions/notes/helpers/execplans)
- `project` mode: downstream cloned repos enable full self-improving capture loop

## Quick Start

1. Clone/copy this repo as your base.
2. Fill `UNCONFIRMED` fields in:
- `AGENTS.md`
- `/.agent/CONTEXT.md`
- `/.agent/RUNBOOK.md`
3. Run checks in template mode:

```bash
bash scripts/agent-hygiene-check.sh --mode template
bash scripts/agent-weekly-review.sh --mode template
```

4. In downstream project repos, use project mode:

```bash
bash scripts/agent-hygiene-check.sh --mode project
bash scripts/agent-weekly-review.sh --mode project
```

## Contract Summary

1. Startup order: `INDEX -> CONTINUITY -> CONTEXT -> WORKFLOW -> helpers/INDEX`
2. Substantial task flow: `clarify -> plan -> implement -> validate -> capture`
3. End-of-task capture uses a balanced review:
- what went wrong + prevention
- what went right + measurable improvement
- decision per item: `promote now | pilot backlog | keep local`

## Reference Docs

- Canonical framework guide: `docs/FRAMEWORK_GUIDE.md`
- Subdirectory policy example: `docs/examples/SUBDIR_AGENTS_EXAMPLE.md`
