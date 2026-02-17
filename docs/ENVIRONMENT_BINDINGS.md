# Environment Bindings (Single Environment)

This file defines deploy/observability bindings for the single active environment.

## Required Secret Bindings (Deploy-Only MVP)

### Deploy bindings (current single env uses existing `*_STAGING` names)
- `SJ_GCP_PROJECT_ID_STAGING`
- `SJ_GCP_WORKLOAD_IDENTITY_PROVIDER_STAGING`
- `SJ_GCP_SERVICE_ACCOUNT_STAGING`
- `SJ_DEPLOY_API_CMD_STAGING`
- `SJ_DEPLOY_WORKER_CMD_STAGING`
- `SJ_DEPLOY_WEB_CMD_STAGING`

## Optional Secret Bindings (Observability/Telemetry)

Only required when triggering `deploy.yml` with optional import/validation flags enabled.

- `SJ_API_SERVICE_NAME_STAGING`
- `SJ_WORKER_OTEL_SERVICE_NAME_STAGING`
- `SJ_NOTIFICATION_CHANNELS_STAGING`
- `SJ_API_BASE_URL_STAGING`

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
- The workflow is intentionally single-environment for MVP speed; keep one runtime stable before introducing a second environment.
