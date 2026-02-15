# Environment Bindings (Staging/Production)

This file defines environment-bound values for deploy and optional observability execution.

## Required Secret Bindings (Deploy-Only MVP)

### Shared contract
- `SJ_GCP_PROJECT_ID_<ENV>`: GCP project id.
- `SJ_GCP_WORKLOAD_IDENTITY_PROVIDER_<ENV>`: Workload Identity provider resource.
- `SJ_GCP_SERVICE_ACCOUNT_<ENV>`: Service account email for deploy/import actions.
- `SJ_DEPLOY_API_CMD_<ENV>`: Command that deploys the API for the environment.
- `SJ_DEPLOY_WORKER_CMD_<ENV>`: Command that deploys workers for the environment.
- `SJ_DEPLOY_WEB_CMD_<ENV>`: Command that deploys web for the environment.

### Staging bindings
- `SJ_GCP_PROJECT_ID_STAGING`
- `SJ_GCP_WORKLOAD_IDENTITY_PROVIDER_STAGING`
- `SJ_GCP_SERVICE_ACCOUNT_STAGING`
- `SJ_DEPLOY_API_CMD_STAGING`
- `SJ_DEPLOY_WORKER_CMD_STAGING`
- `SJ_DEPLOY_WEB_CMD_STAGING`

### Production bindings
- `SJ_GCP_PROJECT_ID_PROD`
- `SJ_GCP_WORKLOAD_IDENTITY_PROVIDER_PROD`
- `SJ_GCP_SERVICE_ACCOUNT_PROD`
- `SJ_DEPLOY_API_CMD_PROD`
- `SJ_DEPLOY_WORKER_CMD_PROD`
- `SJ_DEPLOY_WEB_CMD_PROD`

## Optional Secret Bindings (Observability/Telemetry)

Only required when triggering `deploy.yml` with optional import/validation flags enabled.

- `SJ_API_SERVICE_NAME_<ENV>`
- `SJ_WORKER_OTEL_SERVICE_NAME_<ENV>`
- `SJ_NOTIFICATION_CHANNELS_<ENV>`
- `SJ_API_BASE_URL_<ENV>`

## Local Binding Check

```bash
SJ_OBS_ENVIRONMENT=staging \
SJ_OBS_API_CLOUD_RUN_SERVICE=sloppy-jobulator-api-staging \
SJ_OBS_WORKER_OTEL_SERVICE=sloppy-jobulator-workers-staging \
SJ_OBS_NOTIFICATION_CHANNELS="projects/<project>/notificationChannels/<id>" \
python3 scripts/bind-observability-assets.py
```

## Notes
- `deploy.yml` now supports deploy-only runs by default; observability import and telemetry validation are opt-in.
- Use real metric labels from staged runtime (`resource.labels.service_name`, `metric.labels.service_name`, `metric.labels.environment`) before production import.
