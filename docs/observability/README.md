# Observability Baseline (J1/J2)

This folder stores versioned telemetry operating artifacts for Cloud Operations.

## Artifacts
1. `cloud-monitoring-dashboard.json`
- Baseline dashboard for API latency/error, worker throughput, queue backlog, and freshness lag.
2. `alert-policies.yaml`
- Baseline SLO/health alerts for ingest failures, backlog growth, lease expiration growth, and freshness SLA misses.
3. `cloud-monitoring-dashboard.template.json`
- Environment-bindable dashboard template with service/metric label placeholders.
4. `alert-policies.template.yaml`
- Environment-bindable alert policy template with notification channel placeholders.

## Bind + import commands
1. Render environment-bound assets:
```bash
SJ_OBS_ENVIRONMENT=staging \
SJ_OBS_API_CLOUD_RUN_SERVICE=sloppy-jobulator-api-staging \
SJ_OBS_WORKER_OTEL_SERVICE=sloppy-jobulator-workers-staging \
SJ_OBS_NOTIFICATION_CHANNELS="projects/<project>/notificationChannels/<id>" \
python3 scripts/bind-observability-assets.py
```
2. Import rendered dashboard + alert policies:
```bash
GCP_PROJECT_ID="<project>" \
SJ_OBS_ENVIRONMENT=staging \
SJ_OBS_API_CLOUD_RUN_SERVICE=sloppy-jobulator-api-staging \
SJ_OBS_WORKER_OTEL_SERVICE=sloppy-jobulator-workers-staging \
SJ_OBS_NOTIFICATION_CHANNELS="projects/<project>/notificationChannels/<id>" \
bash scripts/import-observability-assets.sh
```
Notes:
- Dashboard import is idempotent by `displayName` (create on first run, update on reruns).
- Alert policy import currently requires the `gcloud alpha` component. If unavailable, set `SJ_OBS_SKIP_ALERT_POLICIES=true` to import only dashboard assets.
3. Validate telemetry quality in the bound environment:
```bash
GCP_PROJECT_ID="<project>" \
SJ_OBS_ENVIRONMENT=staging \
SJ_OBS_API_CLOUD_RUN_SERVICE=sloppy-jobulator-api-staging \
SJ_OBS_WORKER_OTEL_SERVICE=sloppy-jobulator-workers-staging \
SJ_API_BASE_URL="https://api-staging.example.com" \
bash scripts/validate-telemetry-quality.sh
```

## Notes
1. `docs/ENVIRONMENT_BINDINGS.md` is the source of truth for staging/prod secret bindings used by `.github/workflows/deploy.yml`.
2. Custom `custom.googleapis.com/sloppy_jobulator/*` metrics are expected to include `metric.labels.environment` and `metric.labels.service_name` from the OTel pipeline mapping.
