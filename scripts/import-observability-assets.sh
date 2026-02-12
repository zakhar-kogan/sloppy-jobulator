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

gcloud monitoring dashboards create \
  --project "${GCP_PROJECT_ID}" \
  --config-from-file "${dashboard_file}"

gcloud alpha monitoring policies create \
  --project "${GCP_PROJECT_ID}" \
  --policy-from-file "${alerts_file}"

echo "observability assets imported for ${SJ_OBS_ENVIRONMENT}"
