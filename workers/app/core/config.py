from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_base_url: str = "http://localhost:8000"
    module_id: str = "local-processor"
    api_key: str = "local-processor-key"
    poll_interval_seconds: float = 2.0
    max_backoff_seconds: float = 15.0

    model_config = SettingsConfigDict(env_prefix="SJ_WORKER_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
