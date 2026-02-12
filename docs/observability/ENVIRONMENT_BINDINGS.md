# Observability Environment Bindings (J1/J2)

Use this guide to bind telemetry and alert artifacts to a concrete environment.

## Required bindings
1. `GCP_PROJECT_ID`: target GCP project.
2. `SJ_API_SERVICE_NAME`: Cloud Run API service (`resource.label.service_name`).
3. `SJ_WORKER_SERVICE_NAME`: worker service/job label used in metrics.
4. `SJ_ALERT_NOTIFICATION_CHANNELS`: comma-separated channel resource names.
5. `SJ_OTEL_EXPORTER_OTLP_ENDPOINT`: OTLP endpoint for API service.
6. `SJ_WORKER_OTEL_EXPORTER_OTLP_ENDPOINT`: OTLP endpoint for workers.

## Staging example
```bash
export GCP_PROJECT_ID="sloppy-jobulator-staging"
export SJ_API_SERVICE_NAME="sj-api-staging"
export SJ_WORKER_SERVICE_NAME="sj-workers-staging"
export SJ_ALERT_NOTIFICATION_CHANNELS="projects/sloppy-jobulator-staging/notificationChannels/1234567890"
export SJ_OTEL_EXPORTER_OTLP_ENDPOINT="https://otlp.staging.example/v1/traces"
export SJ_WORKER_OTEL_EXPORTER_OTLP_ENDPOINT="https://otlp.staging.example/v1/traces"
```

## Production example
```bash
export GCP_PROJECT_ID="sloppy-jobulator-prod"
export SJ_API_SERVICE_NAME="sj-api-prod"
export SJ_WORKER_SERVICE_NAME="sj-workers-prod"
export SJ_ALERT_NOTIFICATION_CHANNELS="projects/sloppy-jobulator-prod/notificationChannels/0987654321"
export SJ_OTEL_EXPORTER_OTLP_ENDPOINT="https://otlp.prod.example/v1/traces"
export SJ_WORKER_OTEL_EXPORTER_OTLP_ENDPOINT="https://otlp.prod.example/v1/traces"
```

## Dashboard import checklist
1. Replace service filters in `docs/observability/cloud-monitoring-dashboard.json` with `SJ_API_SERVICE_NAME` and worker labels.
2. Import dashboard:
```bash
gcloud monitoring dashboards create \
  --project "${GCP_PROJECT_ID}" \
  --config-from-file docs/observability/cloud-monitoring-dashboard.json
```

## Alert policy import checklist
1. Replace `notificationChannels` in `docs/observability/alert-policies.yaml` with values from `SJ_ALERT_NOTIFICATION_CHANNELS`.
2. Import policies:
```bash
gcloud alpha monitoring policies create \
  --project "${GCP_PROJECT_ID}" \
  --policy-from-file docs/observability/alert-policies.yaml
```

## Runtime telemetry binding
1. API:
- `SJ_OTEL_EXPORTER_OTLP_ENDPOINT=${SJ_OTEL_EXPORTER_OTLP_ENDPOINT}`
- `SJ_OTEL_SERVICE_NAME=${SJ_API_SERVICE_NAME}`
2. Workers:
- `SJ_WORKER_OTEL_EXPORTER_OTLP_ENDPOINT=${SJ_WORKER_OTEL_EXPORTER_OTLP_ENDPOINT}`
- `SJ_WORKER_OTEL_SERVICE_NAME=${SJ_WORKER_SERVICE_NAME}`
