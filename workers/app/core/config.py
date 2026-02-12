from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "dev"
    api_base_url: str = "http://localhost:8000"
    module_id: str = "local-processor"
    api_key: str = "local-processor-key"
    poll_interval_seconds: float = 2.0
    max_backoff_seconds: float = 15.0
    claim_lease_seconds: int = 120
    lease_reaper_interval_seconds: float = 15.0
    lease_reaper_batch_size: int = 100
    freshness_enqueue_interval_seconds: float = 300.0
    freshness_enqueue_batch_size: int = 100
    otel_enabled: bool = True
    otel_service_name: str = "sloppy-jobulator-workers"
    otel_exporter_otlp_endpoint: str | None = None
    otel_exporter_otlp_headers: str | None = None
    otel_trace_sample_ratio: float = 1.0
    otel_log_correlation: bool = True

    model_config = SettingsConfigDict(env_prefix="SJ_WORKER_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
