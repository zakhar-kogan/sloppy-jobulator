#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import sys


def main() -> int:
    env_name = _required("SJ_OBS_ENVIRONMENT")
    api_service = _required("SJ_OBS_API_CLOUD_RUN_SERVICE")
    worker_service = _required("SJ_OBS_WORKER_OTEL_SERVICE")
    channels_raw = _required("SJ_OBS_NOTIFICATION_CHANNELS")
    channels = [value.strip() for value in channels_raw.split(",") if value.strip()]
    if not channels:
        print("SJ_OBS_NOTIFICATION_CHANNELS must contain at least one channel id", file=sys.stderr)
        return 1

    output_root = Path(os.getenv("SJ_OBS_OUTPUT_DIR", f"docs/observability/generated/{env_name}"))
    output_root.mkdir(parents=True, exist_ok=True)

    dashboard_template = Path(
        os.getenv("SJ_OBS_DASHBOARD_TEMPLATE", "docs/observability/cloud-monitoring-dashboard.template.json")
    )
    alerts_template = Path(os.getenv("SJ_OBS_ALERTS_TEMPLATE", "docs/observability/alert-policies.template.yaml"))

    replacements = {
        "__ENVIRONMENT__": env_name,
        "__API_CLOUD_RUN_SERVICE__": api_service,
        "__WORKER_OTEL_SERVICE__": worker_service,
        "__NOTIFICATION_CHANNELS_JSON__": json.dumps(channels),
    }

    dashboard_out = output_root / "cloud-monitoring-dashboard.json"
    alerts_out = output_root / "alert-policies.yaml"
    _render_template(dashboard_template, dashboard_out, replacements)
    _render_template(alerts_template, alerts_out, replacements)

    print(f"rendered_dashboard={dashboard_out}")
    print(f"rendered_alert_policies={alerts_out}")
    return 0


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"missing required env var: {name}")
    return value


def _render_template(template_path: Path, output_path: Path, replacements: dict[str, str]) -> None:
    content = template_path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        content = content.replace(key, value)
    unresolved = [token for token in {"__ENVIRONMENT__", "__API_CLOUD_RUN_SERVICE__", "__WORKER_OTEL_SERVICE__"} if token in content]
    if unresolved:
        raise SystemExit(f"unresolved template tokens in {template_path}: {', '.join(sorted(unresolved))}")
    output_path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
