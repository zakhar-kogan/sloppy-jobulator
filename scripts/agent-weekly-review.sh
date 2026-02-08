#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

mode="template"

usage() {
  cat <<'USAGE'
Usage: bash scripts/agent-weekly-review.sh [--mode template|project]
Defaults to --mode template.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --mode requires a value (template|project)."
        exit 2
      fi
      mode="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1"
      usage
      exit 2
      ;;
  esac
done

if [[ "$mode" != "template" && "$mode" != "project" ]]; then
  echo "ERROR: invalid mode '$mode'. Use template or project."
  exit 2
fi

echo "== Agent Weekly Review =="
echo "Mode: $mode"
echo

echo "1) Running hygiene checks"
"$repo_root/scripts/agent-hygiene-check.sh" --mode "$mode"
echo

if [[ "$mode" == "project" ]]; then
  echo "2) Notes older than 30 days (review for prune/promotion)"
  if find .agent/notes -type f -name "*.md" ! -name "TEMPLATE.md" -mtime +30 | grep -q .; then
    find .agent/notes -type f -name "*.md" ! -name "TEMPLATE.md" -mtime +30 | sort
  else
    echo "(none)"
  fi
  echo

  echo "3) Helpers older than 45 days (review for STABLE/RETIRED/prune)"
  if find .agent/helpers -type f -name "*.md" ! -name "INDEX.md" ! -name "TEMPLATE.md" -mtime +45 | grep -q .; then
    find .agent/helpers -type f -name "*.md" ! -name "INDEX.md" ! -name "TEMPLATE.md" -mtime +45 | sort
  else
    echo "(none)"
  fi
  echo
else
  echo "2) Unexpected state files in template mode"
  state_files="$({
    find .agent/notes -maxdepth 1 -type f ! -name ".gitkeep" ! -name "TEMPLATE.md";
    find .agent/helpers -maxdepth 1 -type f ! -name "INDEX.md" ! -name "TEMPLATE.md" ! -name ".gitkeep";
    find .agent/execplans/active -maxdepth 1 -type f ! -name ".gitkeep" ! -name "EP-TEMPLATE.md";
    find .agent/execplans/archive -maxdepth 1 -type f ! -name ".gitkeep";
  } | sort)"

  if [[ -n "$state_files" ]]; then
    echo "$state_files"
  else
    echo "(none)"
  fi
  echo

  echo "3) Stateful template placeholders accidentally filled"
  continuity_dates="$(rg -n "^- \`[0-9]{4}-[0-9]{2}-[0-9]{2}\`" .agent/CONTINUITY.md || true)"
  decision_dates="$(rg -n "^- Date: [0-9]{4}-[0-9]{2}-[0-9]{2}" .agent/DECISIONS.md || true)"
  filled_snapshot="$(rg -n "^(Goal|Now|Next|Open Questions):[[:space:]]+[^[:space:]]+" .agent/CONTINUITY.md || true)"

  if [[ -z "$continuity_dates" && -z "$decision_dates" && -z "$filled_snapshot" ]]; then
    echo "(none)"
  else
    [[ -n "$filled_snapshot" ]] && echo "$filled_snapshot"
    [[ -n "$continuity_dates" ]] && echo "$continuity_dates"
    [[ -n "$decision_dates" ]] && echo "$decision_dates"
  fi
  echo
fi

echo "4) Contradiction/duplication candidates"
echo "Repeated headings (count + heading):"
repeated_headings="$(rg -n '^## ' AGENTS.md .agent README.md docs 2>/dev/null | sed -E 's/^[^:]+:[0-9]+:##[[:space:]]*//' | sort | uniq -cd | awk '$1 > 1' || true)"
if [[ -n "$repeated_headings" ]]; then
  echo "$repeated_headings"
else
  echo "(none)"
fi
echo

echo "Potential conflicting stateful instructions (review for mode gating):"
stateful_guidance="$(rg -n -i 'update .*continuity|create .*note|dated note|update .*decisions|add a short note' AGENTS.md .agent/*.md README.md docs/*.md 2>/dev/null || true)"
if [[ -n "$stateful_guidance" ]]; then
  echo "$stateful_guidance"
else
  echo "(none)"
fi
echo

echo "5) Remaining UNCONFIRMED placeholders"
if rg -n "UNCONFIRMED" AGENTS.md .agent; then
  true
else
  echo "(none)"
fi
echo

echo "6) Suggested next actions"
if [[ "$mode" == "template" ]]; then
  echo "- keep scaffold files sanitized (no live continuity/decision/note/helper/plan entries)"
  echo "- remove duplicated policy text and keep one canonical source"
  echo "- prune ineffective rules that do not prevent failures or save time"
  echo "- update unresolved UNCONFIRMED command fields"
else
  echo "- prune stale task notes"
  echo "- review helper statuses and promote stable helper rules"
  echo "- promote repeated learnings into RUNBOOK/PATTERNS/DECISIONS"
  echo "- update unresolved UNCONFIRMED command fields"
fi
