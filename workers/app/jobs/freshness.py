from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def execute_check_freshness(job: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    raw_inputs = job.get("inputs_json")
    inputs: dict[str, Any] = raw_inputs if isinstance(raw_inputs, dict) else {}

    posting_status = _as_text(inputs.get("posting_status")) or "active"
    stale_after_hours = _as_int(inputs.get("stale_after_hours"), default=24)
    archive_after_hours = max(stale_after_hours, _as_int(inputs.get("archive_after_hours"), default=72))
    posting_updated_at = _parse_timestamp(inputs.get("posting_updated_at"))

    if posting_updated_at is None:
        return {
            "handled": True,
            "kind": job.get("kind"),
            "target_type": job.get("target_type"),
            "target_id": job.get("target_id"),
            "recommended_status": None,
            "reason": "missing_or_invalid_posting_updated_at",
        }

    age_hours = max(0.0, (current - posting_updated_at).total_seconds() / 3600.0)
    recommended_status: str | None = None
    reason = "freshness_within_window"

    if posting_status == "active" and age_hours >= stale_after_hours:
        recommended_status = "stale"
        reason = "stale_threshold_exceeded"
    elif posting_status == "stale" and age_hours >= archive_after_hours:
        recommended_status = "archived"
        reason = "archive_threshold_exceeded"

    return {
        "handled": True,
        "kind": job.get("kind"),
        "target_type": job.get("target_type"),
        "target_id": job.get("target_id"),
        "recommended_status": recommended_status,
        "reason": reason,
        "age_hours": round(age_hours, 3),
        "posting_status": posting_status,
        "stale_after_hours": stale_after_hours,
        "archive_after_hours": archive_after_hours,
    }


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _as_int(value: Any, *, default: int) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def _parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
