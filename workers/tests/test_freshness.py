from datetime import datetime, timedelta, timezone

from app.jobs.freshness import execute_check_freshness


def test_check_freshness_marks_active_as_stale_when_threshold_exceeded() -> None:
    now = datetime.now(timezone.utc)
    job = {
        "kind": "check_freshness",
        "target_type": "posting",
        "target_id": "posting-1",
        "inputs_json": {
            "posting_status": "active",
            "posting_updated_at": (now - timedelta(hours=30)).isoformat(),
            "stale_after_hours": 24,
            "archive_after_hours": 72,
        },
    }

    result = execute_check_freshness(job, now=now)
    assert result["recommended_status"] == "stale"
    assert result["reason"] == "stale_threshold_exceeded"


def test_check_freshness_marks_stale_as_archived_when_archive_threshold_exceeded() -> None:
    now = datetime.now(timezone.utc)
    job = {
        "kind": "check_freshness",
        "target_type": "posting",
        "target_id": "posting-2",
        "inputs_json": {
            "posting_status": "stale",
            "posting_updated_at": (now - timedelta(hours=80)).isoformat(),
            "stale_after_hours": 24,
            "archive_after_hours": 72,
        },
    }

    result = execute_check_freshness(job, now=now)
    assert result["recommended_status"] == "archived"
    assert result["reason"] == "archive_threshold_exceeded"


def test_check_freshness_returns_no_change_inside_window() -> None:
    now = datetime.now(timezone.utc)
    job = {
        "kind": "check_freshness",
        "target_type": "posting",
        "target_id": "posting-3",
        "inputs_json": {
            "posting_status": "active",
            "posting_updated_at": (now - timedelta(hours=6)).isoformat(),
            "stale_after_hours": 24,
            "archive_after_hours": 72,
        },
    }

    result = execute_check_freshness(job, now=now)
    assert result["recommended_status"] is None
    assert result["reason"] == "freshness_within_window"


def test_check_freshness_handles_missing_timestamp() -> None:
    result = execute_check_freshness(
        {
            "kind": "check_freshness",
            "target_type": "posting",
            "target_id": "posting-4",
            "inputs_json": {"posting_status": "active"},
        }
    )

    assert result["recommended_status"] is None
    assert result["reason"] == "missing_or_invalid_posting_updated_at"
