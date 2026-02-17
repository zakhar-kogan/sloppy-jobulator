from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.jobs.redirects import execute_resolve_url_redirects


def test_resolve_url_redirects_follows_chain_and_normalizes_url() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "http://example.edu/jobs/role?utm_source=feed":
            return httpx.Response(
                status_code=301,
                headers={"location": "/jobs/role-final?sessionId=abc&utm_medium=email"},
                request=request,
            )
        if str(request.url) == "http://example.edu/jobs/role-final?sessionId=abc&utm_medium=email":
            return httpx.Response(status_code=200, request=request)
        return httpx.Response(status_code=404, request=request)

    async def run() -> dict[str, Any]:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport, follow_redirects=False) as client:
            return await execute_resolve_url_redirects(
                {
                    "kind": "resolve_url_redirects",
                    "target_type": "discovery",
                    "target_id": "discovery-1",
                    "inputs_json": {
                        "url": "http://example.edu/jobs/role?utm_source=feed",
                        "normalization_overrides_json": (
                            '{"example.edu":{"strip_query_params":["sessionid"],"force_https":true}}'
                        ),
                    },
                },
                client=client,
            )

    result = asyncio.run(run())
    assert result["reason"] == "resolved"
    assert result["redirect_hop_count"] == 1
    assert result["resolved_url"] == "http://example.edu/jobs/role-final?sessionId=abc&utm_medium=email"
    assert result["resolved_normalized_url"] == "https://example.edu/jobs/role-final"
    assert isinstance(result["resolved_canonical_hash"], str)
    assert len(result["resolved_canonical_hash"]) == 64


def test_resolve_url_redirects_detects_redirect_loop() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://loop.example.edu/a":
            return httpx.Response(status_code=302, headers={"location": "/b"}, request=request)
        if str(request.url) == "https://loop.example.edu/b":
            return httpx.Response(status_code=302, headers={"location": "/a"}, request=request)
        return httpx.Response(status_code=404, request=request)

    async def run() -> dict[str, Any]:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport, follow_redirects=False) as client:
            return await execute_resolve_url_redirects(
                {
                    "kind": "resolve_url_redirects",
                    "target_type": "discovery",
                    "target_id": "discovery-loop",
                    "inputs_json": {"url": "https://loop.example.edu/a", "max_hops": 10},
                },
                client=client,
            )

    result = asyncio.run(run())
    assert result["reason"] == "redirect_loop_detected"
    assert result["redirect_hop_count"] == 2
    assert result["resolved_url"] == "https://loop.example.edu/a"


def test_resolve_url_redirects_handles_missing_url() -> None:
    result = asyncio.run(
        execute_resolve_url_redirects(
            {
                "kind": "resolve_url_redirects",
                "target_type": "discovery",
                "target_id": "discovery-missing",
                "inputs_json": {},
            }
        )
    )
    assert result["reason"] == "missing_url"
    assert result["redirect_hop_count"] == 0


def test_resolve_url_redirects_uses_configured_timeout(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeAsyncClient:
        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, headers: dict[str, str]) -> httpx.Response:
            request = httpx.Request("GET", url, headers=headers)
            return httpx.Response(status_code=200, request=request)

    def fake_async_client(*args: Any, **kwargs: Any) -> FakeAsyncClient:
        captured.update(kwargs)
        return FakeAsyncClient()

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)
    result = asyncio.run(
        execute_resolve_url_redirects(
            {
                "kind": "resolve_url_redirects",
                "target_type": "discovery",
                "target_id": "discovery-timeout",
                "inputs_json": {"url": "https://example.edu/jobs/role"},
            },
            timeout_seconds=3.5,
        )
    )

    assert captured["timeout"] == 3.5
    assert captured["follow_redirects"] is False
    assert result["reason"] == "resolved"
