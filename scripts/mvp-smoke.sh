#!/usr/bin/env bash

set -euo pipefail

if [[ -z "${SJ_API_BASE_URL:-}" ]]; then
  echo "SJ_API_BASE_URL is required" >&2
  exit 1
fi

api_base="${SJ_API_BASE_URL%/}"
connector_module_id="${SJ_CONNECTOR_MODULE_ID:-local-connector}"
connector_api_key="${SJ_CONNECTOR_API_KEY:-local-connector-key}"
processor_module_id="${SJ_PROCESSOR_MODULE_ID:-local-processor}"
processor_api_key="${SJ_PROCESSOR_API_KEY:-local-processor-key}"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
external_id="smoke-${stamp}"
canonical_url="https://example.edu/jobs/${external_id}"

echo "smoke: GET ${api_base}/"
root_code="$(curl -sS -o /tmp/mvp-smoke-root.json -w "%{http_code}" "${api_base}/")"
if [[ "${root_code}" != "200" ]]; then
  echo "smoke failed: root returned ${root_code}" >&2
  cat /tmp/mvp-smoke-root.json >&2
  exit 1
fi

echo "smoke: GET ${api_base}/postings?limit=1"
postings_code="$(curl -sS -o /tmp/mvp-smoke-postings-before.json -w "%{http_code}" "${api_base}/postings?limit=1")"
if [[ "${postings_code}" != "200" ]]; then
  echo "smoke failed: postings returned ${postings_code}" >&2
  cat /tmp/mvp-smoke-postings-before.json >&2
  exit 1
fi

discovered_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
discovery_payload="$(cat <<JSON
{"origin_module_id":"${connector_module_id}","external_id":"${external_id}","discovered_at":"${discovered_at}","url":"${canonical_url}","title_hint":"Smoke Position","text_hint":"MVP smoke flow","metadata":{"source":"mvp-smoke"}}
JSON
)"

echo "smoke: POST ${api_base}/discoveries"
discovery_code="$(
  curl -sS -o /tmp/mvp-smoke-discovery.json -w "%{http_code}" \
    -X POST "${api_base}/discoveries" \
    -H "Content-Type: application/json" \
    -H "X-Module-Id: ${connector_module_id}" \
    -H "X-API-Key: ${connector_api_key}" \
    --data "${discovery_payload}"
)"
if [[ "${discovery_code}" != "202" ]]; then
  echo "smoke failed: discovery returned ${discovery_code}" >&2
  cat /tmp/mvp-smoke-discovery.json >&2
  exit 1
fi

discovery_id="$(
  python - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path("/tmp/mvp-smoke-discovery.json").read_text())
print(payload.get("discovery_id", ""))
PY
)"
if [[ -z "${discovery_id}" ]]; then
  echo "smoke failed: discovery_id missing" >&2
  cat /tmp/mvp-smoke-discovery.json >&2
  exit 1
fi

echo "smoke: GET ${api_base}/jobs?limit=20"
jobs_code="$(
  curl -sS -o /tmp/mvp-smoke-jobs.json -w "%{http_code}" \
    "${api_base}/jobs?limit=20" \
    -H "X-Module-Id: ${processor_module_id}" \
    -H "X-API-Key: ${processor_api_key}"
)"
if [[ "${jobs_code}" != "200" ]]; then
  echo "smoke failed: jobs returned ${jobs_code}" >&2
  cat /tmp/mvp-smoke-jobs.json >&2
  exit 1
fi

job_id="$(
  python - <<'PY'
import json
from pathlib import Path
jobs = json.loads(Path("/tmp/mvp-smoke-jobs.json").read_text())
match = next((row for row in jobs if row.get("kind") == "extract" and row.get("target_id")), None)
print(match.get("id", "") if match else "")
PY
)"
if [[ -z "${job_id}" ]]; then
  echo "smoke failed: extract job not found in queue" >&2
  cat /tmp/mvp-smoke-jobs.json >&2
  exit 1
fi

echo "smoke: POST ${api_base}/jobs/${job_id}/claim"
claim_code="$(
  curl -sS -o /tmp/mvp-smoke-claim.json -w "%{http_code}" \
    -X POST "${api_base}/jobs/${job_id}/claim" \
    -H "Content-Type: application/json" \
    -H "X-Module-Id: ${processor_module_id}" \
    -H "X-API-Key: ${processor_api_key}" \
    --data '{"lease_seconds":120}'
)"
if [[ "${claim_code}" != "200" ]]; then
  echo "smoke failed: claim returned ${claim_code}" >&2
  cat /tmp/mvp-smoke-claim.json >&2
  exit 1
fi

canonical_hash="$(
  python - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path("/tmp/mvp-smoke-discovery.json").read_text())
print(payload.get("canonical_hash", ""))
PY
)"
if [[ -z "${canonical_hash}" ]]; then
  echo "smoke failed: canonical_hash missing" >&2
  cat /tmp/mvp-smoke-discovery.json >&2
  exit 1
fi

result_payload="$(cat <<JSON
{"status":"done","result_json":{"dedupe_confidence":0.99,"risk_flags":["manual_review_low_confidence"],"posting":{"title":"Smoke Position","organization_name":"Example University","canonical_url":"${canonical_url}","normalized_url":"${canonical_url}","canonical_hash":"${canonical_hash}","country":"US","remote":true,"tags":["smoke","mvp"],"areas":["testing"],"description_text":"MVP smoke posting","source_refs":[{"kind":"discovery","id":"${discovery_id}"}]}}}
JSON
)"

echo "smoke: POST ${api_base}/jobs/${job_id}/result"
result_code="$(
  curl -sS -o /tmp/mvp-smoke-result.json -w "%{http_code}" \
    -X POST "${api_base}/jobs/${job_id}/result" \
    -H "Content-Type: application/json" \
    -H "X-Module-Id: ${processor_module_id}" \
    -H "X-API-Key: ${processor_api_key}" \
    --data "${result_payload}"
)"
if [[ "${result_code}" != "200" ]]; then
  echo "smoke failed: result returned ${result_code}" >&2
  cat /tmp/mvp-smoke-result.json >&2
  exit 1
fi

echo "smoke: GET ${api_base}/postings?limit=20"
postings_after_code="$(curl -sS -o /tmp/mvp-smoke-postings-after.json -w "%{http_code}" "${api_base}/postings?limit=20")"
if [[ "${postings_after_code}" != "200" ]]; then
  echo "smoke failed: postings after returned ${postings_after_code}" >&2
  cat /tmp/mvp-smoke-postings-after.json >&2
  exit 1
fi

found_posting="$(
  python - <<'PY'
import json
from pathlib import Path
rows = json.loads(Path("/tmp/mvp-smoke-postings-after.json").read_text())
match = next((row for row in rows if row.get("canonical_url", "").startswith("https://example.edu/jobs/smoke-")), None)
print("yes" if match else "no")
PY
)"
if [[ "${found_posting}" != "yes" ]]; then
  echo "smoke failed: smoke posting not found in public postings list" >&2
  cat /tmp/mvp-smoke-postings-after.json >&2
  exit 1
fi

echo "mvp smoke: PASS"
