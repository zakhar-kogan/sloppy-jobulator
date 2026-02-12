from __future__ import annotations

from typing import Any

from app.jobs.freshness import execute_check_freshness
from app.jobs.redirects import execute_resolve_url_redirects


async def execute_job(job: dict[str, Any], *, redirect_resolution_timeout_seconds: float = 10.0) -> dict[str, Any]:
    kind = job.get("kind")
    if kind == "check_freshness":
        return execute_check_freshness(job)
    if kind == "resolve_url_redirects":
        return await execute_resolve_url_redirects(job, timeout_seconds=redirect_resolution_timeout_seconds)

    return {
        "handled": True,
        "kind": kind,
        "target_type": job.get("target_type"),
        "target_id": job.get("target_id"),
    }
