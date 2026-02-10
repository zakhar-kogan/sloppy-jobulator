from __future__ import annotations

from typing import Any

from app.jobs.freshness import execute_check_freshness


async def execute_job(job: dict[str, Any]) -> dict[str, Any]:
    if job.get("kind") == "check_freshness":
        return execute_check_freshness(job)

    return {
        "handled": True,
        "kind": job.get("kind"),
        "target_type": job.get("target_type"),
        "target_id": job.get("target_id"),
    }
