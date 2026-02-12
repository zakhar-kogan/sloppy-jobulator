from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "sloppy-jobulator-api"
    environment: str = "dev"
    api_key_header: str = "X-API-Key"
    database_url: str | None = None
    database_pool_min_size: int = 1
    database_pool_max_size: int = 10
    job_max_attempts: int = 3
    job_retry_base_seconds: int = 30
    job_retry_max_seconds: int = 600
    freshness_check_interval_hours: int = 24
    freshness_stale_after_hours: int = 24
    freshness_archive_after_hours: int = 72
    enable_redirect_resolution_jobs: bool = False
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    auth_timeout_seconds: float = 5.0
    otel_enabled: bool = True
    otel_service_name: str = "sloppy-jobulator-api"
    otel_exporter_otlp_endpoint: str | None = None
    otel_exporter_otlp_headers: str | None = None
    otel_trace_sample_ratio: float = 1.0
    otel_log_correlation: bool = True
    url_normalization_overrides_json: str | None = None

    model_config = SettingsConfigDict(env_prefix="SJ_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
