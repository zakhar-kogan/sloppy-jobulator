from __future__ import annotations

from typing import Any

from app.jobs.freshness import execute_check_freshness
from app.jobs.redirects import execute_resolve_url_redirects


async def execute_job(
    job: dict[str, Any],
    *,
    redirect_resolution_timeout_seconds: float | None = None,
) -> dict[str, Any]:
    if job.get("kind") == "check_freshness":
        return execute_check_freshness(job)
    if job.get("kind") == "resolve_url_redirects":
        timeout_seconds = (
            redirect_resolution_timeout_seconds
            if redirect_resolution_timeout_seconds is not None
            else 10.0
        )
        return await execute_resolve_url_redirects(job, timeout_seconds=timeout_seconds)

    return {
        "handled": True,
        "kind": job.get("kind"),
        "target_type": job.get("target_type"),
        "target_id": job.get("target_id"),
    }
