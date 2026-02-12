#!/usr/bin/env bash
set -euo pipefail

required_vars=(
  GCP_PROJECT_ID
  SJ_OBS_ENVIRONMENT
  SJ_OBS_API_CLOUD_RUN_SERVICE
  SJ_OBS_WORKER_OTEL_SERVICE
  SJ_API_BASE_URL
)
for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "missing required env var: ${var_name}" >&2
    exit 1
  fi
done

echo "telemetry smoke: calling ${SJ_API_BASE_URL}/healthz"
curl --fail --silent --show-error "${SJ_API_BASE_URL}/healthz" >/dev/null

window_start="$(date -u -v-45M '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u -d '45 minutes ago' '+%Y-%m-%dT%H:%M:%SZ')"

echo "checking API request_count series for ${SJ_OBS_API_CLOUD_RUN_SERVICE}"
api_series_count="$(
  gcloud monitoring time-series list \
    --project "${GCP_PROJECT_ID}" \
    --filter "metric.type=\"run.googleapis.com/request_count\" AND resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SJ_OBS_API_CLOUD_RUN_SERVICE}\"" \
    --interval-start "${window_start}" \
    --limit 1 \
    --format 'value(points[0].value.int64Value)' \
    | wc -l | tr -d '[:space:]'
)"
if [[ "${api_series_count}" == "0" ]]; then
  echo "no API request_count telemetry found for service ${SJ_OBS_API_CLOUD_RUN_SERVICE}" >&2
  exit 1
fi

echo "checking worker custom backlog series for ${SJ_OBS_WORKER_OTEL_SERVICE}"
worker_series_count="$(
  gcloud monitoring time-series list \
    --project "${GCP_PROJECT_ID}" \
    --filter "metric.type=\"custom.googleapis.com/sloppy_jobulator/jobs/backlog\" AND resource.type=\"global\" AND metric.labels.environment=\"${SJ_OBS_ENVIRONMENT}\" AND metric.labels.service_name=\"${SJ_OBS_WORKER_OTEL_SERVICE}\"" \
    --interval-start "${window_start}" \
    --limit 1 \
    --format 'value(points[0].value.doubleValue)' \
    | wc -l | tr -d '[:space:]'
)"
if [[ "${worker_series_count}" == "0" ]]; then
  echo "no worker backlog telemetry found for service ${SJ_OBS_WORKER_OTEL_SERVICE} env ${SJ_OBS_ENVIRONMENT}" >&2
  exit 1
fi

echo "telemetry quality check passed for ${SJ_OBS_ENVIRONMENT}"
