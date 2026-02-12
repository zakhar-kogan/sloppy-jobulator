from __future__ import annotations

from dataclasses import dataclass
import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

from app.core.config import Settings

_BASE_LOG_RECORD_FACTORY = logging.getLogRecordFactory()
_LOG_CORRELATION_INSTALLED = False
_HTTPX_INSTRUMENTOR = HTTPXClientInstrumentor()


@dataclass(slots=True)
class TelemetryRuntime:
    enabled: bool
    provider: TracerProvider | None


def configure_worker_logging() -> None:
    _install_log_correlation()
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s trace_id=%(trace_id)s span_id=%(span_id)s %(message)s",
    )


def setup_worker_telemetry(settings: Settings) -> TelemetryRuntime:
    if not settings.otel_enabled:
        return TelemetryRuntime(enabled=False, provider=None)

    if settings.otel_log_correlation:
        _install_log_correlation()

    provider = TracerProvider(
        resource=Resource.create(
            {
                SERVICE_NAME: settings.otel_service_name,
                DEPLOYMENT_ENVIRONMENT: settings.environment,
            }
        ),
        sampler=TraceIdRatioBased(settings.otel_trace_sample_ratio),
    )
    exporter = _build_exporter(settings)
    if exporter is not None:
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _HTTPX_INSTRUMENTOR.instrument()
    return TelemetryRuntime(enabled=True, provider=provider)


def shutdown_worker_telemetry(runtime: TelemetryRuntime) -> None:
    if not runtime.enabled:
        return
    _HTTPX_INSTRUMENTOR.uninstrument()
    if runtime.provider is not None:
        runtime.provider.force_flush()
        runtime.provider.shutdown()


def _build_exporter(settings: Settings) -> OTLPSpanExporter | None:
    endpoint = settings.otel_exporter_otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    if endpoint is None:
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        logging.getLogger(__name__).info(
            "OTel exporter endpoint not set; spans remain local-only for service=%s",
            settings.otel_service_name,
        )
        return None

    headers = _parse_headers(settings.otel_exporter_otlp_headers or os.getenv("OTEL_EXPORTER_OTLP_HEADERS"))
    if endpoint and headers:
        return OTLPSpanExporter(endpoint=endpoint, headers=headers)
    if endpoint:
        return OTLPSpanExporter(endpoint=endpoint)
    if headers:
        return OTLPSpanExporter(headers=headers)
    return OTLPSpanExporter()


def _parse_headers(raw: str | None) -> dict[str, str]:
    if raw is None:
        return {}
    parsed: dict[str, str] = {}
    for item in raw.split(","):
        key, separator, value = item.partition("=")
        if not separator:
            continue
        stripped_key = key.strip()
        stripped_value = value.strip()
        if stripped_key:
            parsed[stripped_key] = stripped_value
    return parsed


def _install_log_correlation() -> None:
    global _LOG_CORRELATION_INSTALLED
    if _LOG_CORRELATION_INSTALLED:
        return

    def record_factory(*args: object, **kwargs: object) -> logging.LogRecord:
        record = _BASE_LOG_RECORD_FACTORY(*args, **kwargs)
        span = trace.get_current_span()
        context = span.get_span_context()
        if context.is_valid:
            record.trace_id = format(context.trace_id, "032x")
            record.span_id = format(context.span_id, "016x")
        else:
            record.trace_id = "0" * 32
            record.span_id = "0" * 16
        return record

    logging.setLogRecordFactory(record_factory)
    _LOG_CORRELATION_INSTALLED = True
