from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "sloppy-jobulator-api"
    environment: str = "dev"
    api_key_header: str = "X-API-Key"

    model_config = SettingsConfigDict(env_prefix="SJ_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
