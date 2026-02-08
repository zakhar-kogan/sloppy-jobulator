from datetime import datetime, timedelta, timezone

from app.jobs.lease_reaper import should_requeue


def test_should_requeue_when_expired() -> None:
    now = datetime.now(timezone.utc)
    job = {"status": "claimed", "lease_expires_at": (now - timedelta(seconds=5)).isoformat()}
    assert should_requeue(job, now=now)


def test_should_not_requeue_when_not_claimed() -> None:
    now = datetime.now(timezone.utc)
    job = {"status": "done", "lease_expires_at": (now - timedelta(seconds=5)).isoformat()}
    assert not should_requeue(job, now=now)
