from __future__ import annotations

import asyncio
import logging
import random
import time

from opentelemetry import trace

from app.core.config import get_settings
from app.core.telemetry import (
    configure_worker_logging,
    setup_worker_telemetry,
    shutdown_worker_telemetry,
)
from app.jobs.executor import execute_job
from app.services.job_client import JobClient

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


async def run_worker() -> None:
    settings = get_settings()
    configure_worker_logging()
    telemetry_runtime = setup_worker_telemetry(settings)
    client = JobClient(
        base_url=settings.api_base_url,
        module_id=settings.module_id,
        api_key=settings.api_key,
    )

    backoff = settings.poll_interval_seconds
    last_reap_at = 0.0
    last_freshness_enqueue_at = 0.0

    try:
        while True:
            try:
                with tracer.start_as_current_span("worker.poll_cycle"):
                    now = time.monotonic()
                    if now - last_reap_at >= settings.lease_reaper_interval_seconds:
                        requeued = await client.reap_expired_jobs(limit=settings.lease_reaper_batch_size)
                        if requeued:
                            logger.info("requeued expired leases: %s", requeued)
                        last_reap_at = now

                    if now - last_freshness_enqueue_at >= settings.freshness_enqueue_interval_seconds:
                        enqueued = await client.enqueue_freshness_jobs(limit=settings.freshness_enqueue_batch_size)
                        if enqueued:
                            logger.info("enqueued freshness jobs: %s", enqueued)
                        last_freshness_enqueue_at = now

                    jobs = await client.get_jobs(limit=5)
                    if not jobs:
                        await asyncio.sleep(settings.poll_interval_seconds)
                        continue

                    for job in jobs:
                        with tracer.start_as_current_span("worker.process_job") as job_span:
                            job_span.set_attribute("job.id", job["id"])
                            claimed = await client.claim_job(job["id"], lease_seconds=settings.claim_lease_seconds)
                            try:
                                result = await execute_job(
                                    claimed,
                                    redirect_resolution_timeout_seconds=settings.redirect_resolution_timeout_seconds,
                                )
                            except Exception as exc:  # pragma: no cover - bootstrap robustness
                                await client.submit_result(
                                    claimed["id"],
                                    status="failed",
                                    error_json={"error": str(exc)},
                                )
                                logger.exception("job execution failed for id=%s", claimed["id"])
                                continue

                            await client.submit_result(claimed["id"], status="done", result_json=result)

                    backoff = settings.poll_interval_seconds
            except Exception as exc:  # pragma: no cover - bootstrap robustness
                jitter = random.uniform(0.0, 0.5)
                sleep_for = min(backoff * (2.0 + jitter), settings.max_backoff_seconds)
                logger.exception("worker iteration failed: %s; retry in %.1fs", exc, sleep_for)
                await asyncio.sleep(sleep_for)
                backoff = sleep_for
    finally:
        shutdown_worker_telemetry(telemetry_runtime)


if __name__ == "__main__":
    asyncio.run(run_worker())
