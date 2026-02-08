from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone

from app.core.config import get_settings
from app.jobs.executor import execute_job
from app.jobs.lease_reaper import should_requeue
from app.services.job_client import JobClient


async def run_worker() -> None:
    settings = get_settings()
    client = JobClient(
        base_url=settings.api_base_url,
        module_id=settings.module_id,
        api_key=settings.api_key,
    )

    backoff = settings.poll_interval_seconds

    while True:
        try:
            jobs = await client.get_jobs(limit=5)
            if not jobs:
                await asyncio.sleep(settings.poll_interval_seconds)
                continue

            for job in jobs:
                if should_requeue(job, now=datetime.now(timezone.utc)):
                    continue

                claimed = await client.claim_job(job["id"], lease_seconds=120)
                result = await execute_job(claimed)
                await client.submit_result(claimed["id"], status="done", result_json=result)

            backoff = settings.poll_interval_seconds
        except Exception as exc:  # pragma: no cover - bootstrap robustness
            jitter = random.uniform(0.0, 0.5)
            sleep_for = min(backoff * (2.0 + jitter), settings.max_backoff_seconds)
            print(f"worker iteration failed: {exc}; retry in {sleep_for:.1f}s")
            await asyncio.sleep(sleep_for)
            backoff = sleep_for


if __name__ == "__main__":
    asyncio.run(run_worker())
