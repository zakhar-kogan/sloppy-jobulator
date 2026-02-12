# Observability Baseline (J1/J2)

This folder stores versioned telemetry operating artifacts for Cloud Operations.

## Artifacts
1. `cloud-monitoring-dashboard.json`
- Baseline dashboard for API latency/error, worker throughput, queue backlog, and freshness lag.
2. `alert-policies.yaml`
- Baseline SLO/health alerts for ingest failures, backlog growth, lease expiration growth, and freshness SLA misses.

## Import commands
1. Dashboard:
```bash
gcloud monitoring dashboards create \
  --project "${GCP_PROJECT_ID}" \
  --config-from-file docs/observability/cloud-monitoring-dashboard.json
```
2. Alert policies:
```bash
gcloud alpha monitoring policies create \
  --project "${GCP_PROJECT_ID}" \
  --policy-from-file docs/observability/alert-policies.yaml
```

## Notes
1. Replace placeholder metric/resource label filters (for example `service_name`) before production import.
2. Custom `custom.googleapis.com/sloppy_jobulator/*` metrics are expected to come from the OTel pipeline exporter mapping.
3. Environment-specific binding examples and required variables are documented in `docs/observability/ENVIRONMENT_BINDINGS.md`.
