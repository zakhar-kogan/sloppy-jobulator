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
api_health_base="${SJ_API_BASE_URL%/}"
api_health_path="${SJ_API_HEALTH_PATH:-/healthz}"
api_health_paths=("${api_health_path}" "/")
health_ok=false
for candidate_path in "${api_health_paths[@]}"; do
  normalized_path="/${candidate_path#/}"
  if curl --fail --silent --show-error "${api_health_base}${normalized_path}" >/dev/null; then
    echo "api health probe succeeded at ${normalized_path}"
    health_ok=true
    break
  fi
done
if [[ "${health_ok}" != "true" ]]; then
  echo "failed to probe API health at ${api_health_base} using paths: ${api_health_paths[*]}" >&2
  exit 1
fi

window_start="$(date -u -v-45M '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u -d '45 minutes ago' '+%Y-%m-%dT%H:%M:%SZ')"
window_end="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
access_token="$(gcloud auth print-access-token)"

count_time_series() {
  local filter="$1"
  local response_file http_code
  response_file="$(mktemp)"
  http_code="$(
    curl --silent --show-error \
      -o "${response_file}" \
      -w '%{http_code}' \
      -G "https://monitoring.googleapis.com/v3/projects/${GCP_PROJECT_ID}/timeSeries" \
      -H "Authorization: Bearer ${access_token}" \
      --data-urlencode "filter=${filter}" \
      --data-urlencode "interval.startTime=${window_start}" \
      --data-urlencode "interval.endTime=${window_end}" \
      --data-urlencode "pageSize=1"
  )"
  if [[ "${http_code}" != "200" ]]; then
    if [[ "${http_code}" == "400" || "${http_code}" == "404" ]]; then
      rm -f "${response_file}"
      echo "0"
      return
    fi
    cat "${response_file}" >&2
    rm -f "${response_file}"
    return 1
  fi
  python3 -c 'import json,sys; print(len(json.load(sys.stdin).get("timeSeries", [])))' < "${response_file}"
  rm -f "${response_file}"
}

echo "checking API request_count series for ${SJ_OBS_API_CLOUD_RUN_SERVICE}"
api_series_count="$(count_time_series "metric.type=\"run.googleapis.com/request_count\" AND resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SJ_OBS_API_CLOUD_RUN_SERVICE}\"")"
if [[ "${api_series_count}" == "0" ]]; then
  echo "no API request_count telemetry found for service ${SJ_OBS_API_CLOUD_RUN_SERVICE}" >&2
  exit 1
fi

echo "checking worker custom backlog series for ${SJ_OBS_WORKER_OTEL_SERVICE}"
worker_series_count="$(count_time_series "metric.type=\"custom.googleapis.com/sloppy_jobulator/jobs/backlog\" AND resource.type=\"global\" AND metric.labels.environment=\"${SJ_OBS_ENVIRONMENT}\" AND metric.labels.service_name=\"${SJ_OBS_WORKER_OTEL_SERVICE}\"")"
if [[ "${worker_series_count}" == "0" ]]; then
  echo "no worker backlog telemetry found for service ${SJ_OBS_WORKER_OTEL_SERVICE} env ${SJ_OBS_ENVIRONMENT}" >&2
  exit 1
fi

echo "telemetry quality check passed for ${SJ_OBS_ENVIRONMENT}"
