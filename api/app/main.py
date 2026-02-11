from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI
from starlette.requests import Request

from app.api.router import api_router
from app.core.config import get_settings
from app.core.telemetry import TelemetryRuntime, setup_api_telemetry, shutdown_api_telemetry
from app.services.repository import get_repository

settings = get_settings()
_telemetry_runtime: TelemetryRuntime | None = None
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        yield
    finally:
        if _telemetry_runtime is not None:
            shutdown_api_telemetry(app, _telemetry_runtime)
        # Ensure asyncpg pool shuts down on app teardown.
        await get_repository().close()
        get_repository.cache_clear()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
_telemetry_runtime = setup_api_telemetry(app, settings)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    started_at = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started_at) * 1000.0
    logger.info(
        "http request method=%s path=%s status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


app.include_router(api_router)
