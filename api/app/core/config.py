from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "sloppy-jobulator-api"
    environment: str = "dev"
    api_key_header: str = "X-API-Key"
    database_url: str | None = None
    database_pool_min_size: int = 1
    database_pool_max_size: int = 10
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    auth_timeout_seconds: float = 5.0

    model_config = SettingsConfigDict(env_prefix="SJ_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
