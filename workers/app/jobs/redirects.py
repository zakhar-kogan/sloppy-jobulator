from __future__ import annotations

from typing import Any

import httpx


async def execute_resolve_url_redirects(
    job: dict[str, Any],
    *,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    raw_inputs = job.get("inputs_json")
    inputs: dict[str, Any] = raw_inputs if isinstance(raw_inputs, dict) else {}
    requested_url = _as_text(inputs.get("url"))

    if not requested_url:
        return {
            "handled": True,
            "kind": job.get("kind"),
            "target_type": job.get("target_type"),
            "target_id": job.get("target_id"),
            "resolved_url": None,
            "reason": "missing_url_input",
        }

    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
        try:
            response = await client.head(requested_url)
            if response.status_code >= 400:
                response = await client.get(requested_url)
        except httpx.HTTPError:
            response = await client.get(requested_url)

    return {
        "handled": True,
        "kind": job.get("kind"),
        "target_type": job.get("target_type"),
        "target_id": job.get("target_id"),
        "requested_url": requested_url,
        "resolved_url": str(response.url),
        "status_code": int(response.status_code),
        "redirect_count": len(response.history),
    }


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None
