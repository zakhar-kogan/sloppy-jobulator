from __future__ import annotations

import asyncio
import random
import time

from app.core.config import get_settings
from app.jobs.executor import execute_job
from app.services.job_client import JobClient


async def run_worker() -> None:
    settings = get_settings()
    client = JobClient(
        base_url=settings.api_base_url,
        module_id=settings.module_id,
        api_key=settings.api_key,
    )

    backoff = settings.poll_interval_seconds
    last_reap_at = 0.0

    while True:
        try:
            now = time.monotonic()
            if now - last_reap_at >= settings.lease_reaper_interval_seconds:
                requeued = await client.reap_expired_jobs(limit=settings.lease_reaper_batch_size)
                if requeued:
                    print(f"requeued expired leases: {requeued}")
                last_reap_at = now

            jobs = await client.get_jobs(limit=5)
            if not jobs:
                await asyncio.sleep(settings.poll_interval_seconds)
                continue

            for job in jobs:
                claimed = await client.claim_job(job["id"], lease_seconds=settings.claim_lease_seconds)
                try:
                    result = await execute_job(claimed)
                except Exception as exc:  # pragma: no cover - bootstrap robustness
                    await client.submit_result(
                        claimed["id"],
                        status="failed",
                        error_json={"error": str(exc)},
                    )
                    continue

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
