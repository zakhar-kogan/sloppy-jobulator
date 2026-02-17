from __future__ import annotations

import asyncio
from typing import Any

from app.jobs import executor


def test_execute_job_passes_timeout_to_redirect_handler(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    async def fake_execute_resolve_url_redirects(
        job: dict[str, Any],
        *,
        client: Any | None = None,
        timeout_seconds: float = 10.0,
    ) -> dict[str, Any]:
        captured["job"] = job
        captured["timeout_seconds"] = timeout_seconds
        captured["client"] = client
        return {"handled": True, "kind": job.get("kind")}

    monkeypatch.setattr(executor, "execute_resolve_url_redirects", fake_execute_resolve_url_redirects)
    result = asyncio.run(
        executor.execute_job(
            {"kind": "resolve_url_redirects", "target_id": "id-1"},
            redirect_resolution_timeout_seconds=2.5,
        )
    )

    assert result["handled"] is True
    assert captured["job"]["target_id"] == "id-1"
    assert captured["timeout_seconds"] == 2.5
    assert captured["client"] is None

