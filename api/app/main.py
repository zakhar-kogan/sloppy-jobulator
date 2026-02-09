from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.services.repository import get_repository

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        yield
    finally:
        # Ensure asyncpg pool shuts down on app teardown.
        await get_repository().close()
        get_repository.cache_clear()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(api_router)
