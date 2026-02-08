from __future__ import annotations

from typing import Any


async def execute_job(job: dict[str, Any]) -> dict[str, Any]:
    """Stub dispatcher for bootstrap.

    Replace with TaskRouter and typed handlers in later phases.
    """
    return {
        "handled": True,
        "kind": job.get("kind"),
        "target_type": job.get("target_type"),
        "target_id": job.get("target_id"),
    }
