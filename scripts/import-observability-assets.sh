#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${GCP_PROJECT_ID:-}" ]]; then
  echo "missing required env var: GCP_PROJECT_ID" >&2
  exit 1
fi

if [[ -z "${SJ_OBS_ENVIRONMENT:-}" ]]; then
  echo "missing required env var: SJ_OBS_ENVIRONMENT" >&2
  exit 1
fi

python3 scripts/bind-observability-assets.py

rendered_dir="${SJ_OBS_OUTPUT_DIR:-docs/observability/generated/${SJ_OBS_ENVIRONMENT}}"
dashboard_file="${rendered_dir}/cloud-monitoring-dashboard.json"
alerts_file="${rendered_dir}/alert-policies.yaml"

dashboard_display_name="$(
  python3 - "${dashboard_file}" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(payload.get("displayName", "").strip())
PY
)"
if [[ -z "${dashboard_display_name}" ]]; then
  echo "dashboard file is missing displayName: ${dashboard_file}" >&2
  exit 1
fi

existing_dashboard_id="$(
  gcloud monitoring dashboards list \
    --project "${GCP_PROJECT_ID}" \
    --format=json \
    | python3 -c '
import json
import sys

target = sys.argv[1]
raw = sys.stdin.read().strip()
rows = json.loads(raw) if raw else []
matches = [row.get("name", "") for row in rows if row.get("displayName") == target and row.get("name")]
print(matches[-1] if matches else "")
' "${dashboard_display_name}"
)"

if [[ -z "${existing_dashboard_id}" ]]; then
  gcloud monitoring dashboards create \
    --project "${GCP_PROJECT_ID}" \
    --config-from-file "${dashboard_file}"
  echo "created dashboard: ${dashboard_display_name}"
else
  dashboard_etag="$(
    gcloud monitoring dashboards describe \
      "${existing_dashboard_id}" \
      --project "${GCP_PROJECT_ID}" \
      --format='value(etag)'
  )"
  if [[ -z "${dashboard_etag}" ]]; then
    echo "could not resolve dashboard etag for ${existing_dashboard_id}" >&2
    exit 1
  fi
  dashboard_update_file="$(mktemp "${TMPDIR:-/tmp}/obs-dashboard-update.XXXXXX.json")"
  python3 - "${dashboard_file}" "${dashboard_etag}" "${dashboard_update_file}" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
payload["etag"] = sys.argv[2]
Path(sys.argv[3]).write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY
  gcloud monitoring dashboards update \
    "${existing_dashboard_id}" \
    --project "${GCP_PROJECT_ID}" \
    --config-from-file "${dashboard_update_file}"
  rm -f "${dashboard_update_file}"
  echo "updated dashboard: ${dashboard_display_name}"
fi

alpha_state="$(
  gcloud components list \
    --filter='id=alpha' \
    --format='value(state.name)'
)"
if [[ "${alpha_state}" != "Installed" ]]; then
  if [[ "${SJ_OBS_SKIP_ALERT_POLICIES:-false}" == "true" ]]; then
    echo "skipping alert policy import because alpha component is not installed"
    exit 0
  fi
  echo "gcloud alpha component is required to import alert policies (${alerts_file})." >&2
  echo "Set SJ_OBS_SKIP_ALERT_POLICIES=true to skip policy import for now." >&2
  exit 1
fi

gcloud alpha monitoring policies create \
  --project "${GCP_PROJECT_ID}" \
  --policy-from-file "${alerts_file}"

echo "observability assets imported for ${SJ_OBS_ENVIRONMENT}"
