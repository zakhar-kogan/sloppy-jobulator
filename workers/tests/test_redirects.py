from __future__ import annotations

import asyncio
from typing import Any

from app.jobs.executor import execute_job
from app.jobs.redirects import execute_resolve_url_redirects


def test_execute_resolve_url_redirects_missing_url_input() -> None:
    result = asyncio.run(
        execute_resolve_url_redirects(
            {
                "kind": "resolve_url_redirects",
                "target_type": "discovery",
                "target_id": "discovery-1",
                "inputs_json": {},
            }
        )
    )
    assert result["handled"] is True
    assert result["reason"] == "missing_url_input"
    assert result["resolved_url"] is None


def test_execute_resolve_url_redirects_uses_followed_location(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self, status_code: int, url: str, history: list[object] | None = None) -> None:
            self.status_code = status_code
            self.url = url
            self.history = history or []

    class FakeClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            return

        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

        async def head(self, _: str) -> FakeResponse:
            return FakeResponse(
                200,
                "https://example.edu/jobs/final",
                history=[object()],
            )

    monkeypatch.setattr("app.jobs.redirects.httpx.AsyncClient", FakeClient)
    result = asyncio.run(
        execute_resolve_url_redirects(
            {
                "kind": "resolve_url_redirects",
                "target_type": "discovery",
                "target_id": "discovery-1",
                "inputs_json": {"url": "https://example.edu/jobs/start"},
            }
        )
    )
    assert result["handled"] is True
    assert result["resolved_url"] == "https://example.edu/jobs/final"
    assert result["redirect_count"] == 1
    assert result["status_code"] == 200


def test_execute_job_routes_redirect_job_kind(monkeypatch) -> None:
    async def _fake_redirect_handler(_: dict[str, Any], *, timeout_seconds: float) -> dict[str, Any]:
        return {"handled": True, "kind": "resolve_url_redirects", "resolved_url": "https://example.edu/jobs/final"}

    monkeypatch.setattr("app.jobs.executor.execute_resolve_url_redirects", _fake_redirect_handler)
    result = asyncio.run(execute_job({"kind": "resolve_url_redirects", "target_type": "discovery", "target_id": "d1"}))
    assert result["kind"] == "resolve_url_redirects"
    assert result["resolved_url"] == "https://example.edu/jobs/final"
