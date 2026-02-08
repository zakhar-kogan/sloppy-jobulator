# Prompts

## Task bootstrap
```text
Read .agent/INDEX.md, .agent/CONTINUITY.md, .agent/CONTEXT.md, and .agent/RUNBOOK.md.
Summarize constraints and acceptance criteria before coding.
```

## End-of-task self-improvement
```text
Before finishing, run a balanced review.
For each item, capture:
1) what went wrong + root cause + prevention rule,
2) what went right + measurable improvement (time/readability/performance/manageability/modularity),
3) decision: promote now | pilot backlog | keep local.
Then apply updates according to mode:
- project mode: update notes/helpers/continuity and promote high-leverage items.
- template mode: keep scaffold sanitized and only improve reusable template policy/docs/scripts.
```

## Helper update after failure
```text
Review the task's failures and repeated friction points.
For each item, either:
1) update an existing helper in `.agent/helpers/`, or
2) create a new helper from `.agent/helpers/TEMPLATE.md`.
Then update `.agent/helpers/INDEX.md` with status and summary.
```

## Repetition mining
```text
Scan .agent/notes/*.md for repeated commands, bugs, decisions, and pilot backlog items.
Propose top reusable items for promotion into durable docs, then apply minimal edits.
```

## Contradiction cleanup
```text
Audit .agent/*.md for conflicting instructions or stale assumptions.
Resolve conflicts and keep one clear current policy.
```
