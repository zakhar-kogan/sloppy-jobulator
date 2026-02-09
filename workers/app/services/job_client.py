from __future__ import annotations

from typing import Any

import httpx


class JobClient:
    def __init__(self, base_url: str, module_id: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-Module-Id": module_id,
            "X-API-Key": api_key,
        }

    async def get_jobs(self, limit: int = 10) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/jobs", params={"limit": limit}, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def claim_job(self, job_id: str, lease_seconds: int = 120) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/jobs/{job_id}/claim",
                json={"lease_seconds": lease_seconds},
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def submit_result(
        self,
        job_id: str,
        *,
        status: str,
        result_json: dict[str, Any] | None = None,
        error_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "status": status,
            "result_json": result_json,
            "error_json": error_json,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{self.base_url}/jobs/{job_id}/result", json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def reap_expired_jobs(self, limit: int = 100) -> int:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/jobs/reap-expired",
                params={"limit": limit},
                headers=self.headers,
            )
            response.raise_for_status()
            payload = response.json()
            return int(payload.get("requeued", 0))
