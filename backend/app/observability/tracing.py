"""Optional OpenTelemetry setup. Disabled by default for zero-dependency local runs."""
from __future__ import annotations

from typing import Any

from app.core.config import settings

_provider: Any | None = None


def configure_tracing(app: Any) -> Any | None:
    """Configure OTEL only when explicitly enabled; return provider for shutdown."""
    global _provider
    if not settings.otel_enabled:
        return None
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create({"service.name": settings.otel_service_name}))
        if settings.otel_export_to_collector:
            provider.add_span_processor(BatchSpanProcessor(
                OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
            ))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
            from app.core.database import engine
            SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine, tracer_provider=provider)
        except Exception:
            # Database instrumentation must never prevent API startup.
            pass
        _provider = provider
        return provider
    except Exception:
        # OTEL is an optional capability. The application remains usable if setup fails.
        return None


def shutdown_tracing(provider: Any | None = None) -> None:
    target = provider or _provider
    if target is not None:
        try:
            target.shutdown()
        except Exception:
            pass
