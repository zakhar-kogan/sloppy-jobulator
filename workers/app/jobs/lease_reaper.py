from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def lease_expired(job: dict[str, Any], now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    lease = job.get("lease_expires_at")
    if not lease:
        return False

    if isinstance(lease, str):
        lease = datetime.fromisoformat(lease.replace("Z", "+00:00"))

    return lease <= now


def should_requeue(job: dict[str, Any], now: datetime | None = None) -> bool:
    return job.get("status") == "claimed" and lease_expired(job, now=now)
