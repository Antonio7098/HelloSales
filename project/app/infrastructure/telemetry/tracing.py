"""OpenTelemetry tracing configuration."""

from contextlib import contextmanager
from typing import Any, Generator

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Span, Status, StatusCode

from app.infrastructure.telemetry.logging import get_logger

logger = get_logger(__name__)

# Global tracer provider reference
_tracer_provider: TracerProvider | None = None


def configure_tracing(
    service_name: str = "hellosales-backend",
    service_version: str = "1.0.0",
    environment: str = "development",
    otlp_endpoint: str | None = None,
    enable_console: bool = False,
) -> TracerProvider:
    """Configure OpenTelemetry tracing.

    Args:
        service_name: Name of the service
        service_version: Version of the service
        environment: Deployment environment (development, staging, production)
        otlp_endpoint: OTLP collector endpoint (e.g., "http://localhost:4317")
        enable_console: Enable console span exporter for debugging

    Returns:
        Configured TracerProvider
    """
    global _tracer_provider

    resource = Resource.create({
        "service.name": service_name,
        "service.version": service_version,
        "deployment.environment": environment,
    })

    provider = TracerProvider(resource=resource)

    # Add OTLP exporter if configured
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(
            "OTLP tracing enabled",
            extra={"endpoint": otlp_endpoint}
        )

    # Add in-memory exporter for testing
    if environment == "test":
        in_memory_exporter = InMemorySpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(in_memory_exporter))

    trace.set_tracer_provider(provider)
    _tracer_provider = provider

    logger.info(
        "OpenTelemetry tracing configured",
        extra={
            "service": service_name,
            "version": service_version,
            "environment": environment,
        }
    )

    return provider


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance.

    Args:
        name: Tracer name (usually __name__)

    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)


def instrument_fastapi(app: Any) -> None:
    """Instrument FastAPI application.

    Args:
        app: FastAPI application instance
    """
    FastAPIInstrumentor.instrument_app(app)
    logger.debug("FastAPI instrumented for tracing")


def instrument_httpx() -> None:
    """Instrument httpx HTTP client."""
    HTTPXClientInstrumentor().instrument()
    logger.debug("httpx instrumented for tracing")


def instrument_sqlalchemy(engine: Any) -> None:
    """Instrument SQLAlchemy engine.

    Args:
        engine: SQLAlchemy engine instance
    """
    SQLAlchemyInstrumentor().instrument(engine=engine)
    logger.debug("SQLAlchemy instrumented for tracing")


@contextmanager
def create_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
) -> Generator[Span, None, None]:
    """Create a traced span context manager.

    Args:
        name: Span name
        attributes: Span attributes
        kind: Span kind (INTERNAL, SERVER, CLIENT, etc.)

    Yields:
        Active span
    """
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span(name, kind=kind) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def set_span_attributes(attributes: dict[str, Any]) -> None:
    """Set attributes on the current span.

    Args:
        attributes: Span attributes to set
    """
    span = trace.get_current_span()
    for key, value in attributes.items():
        if value is not None:
            span.set_attribute(key, value)


def record_exception(exception: Exception, attributes: dict[str, Any] | None = None) -> None:
    """Record an exception on the current span.

    Args:
        exception: Exception to record
        attributes: Additional attributes
    """
    span = trace.get_current_span()
    span.record_exception(exception, attributes=attributes)
    span.set_status(Status(StatusCode.ERROR, str(exception)))


def get_current_trace_id() -> str | None:
    """Get the current trace ID as a hex string.

    Returns:
        Trace ID or None if not in a trace context
    """
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx.is_valid:
        return format(ctx.trace_id, "032x")
    return None


def get_current_span_id() -> str | None:
    """Get the current span ID as a hex string.

    Returns:
        Span ID or None if not in a span context
    """
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx.is_valid:
        return format(ctx.span_id, "016x")
    return None


def shutdown_tracing() -> None:
    """Shutdown the tracer provider and flush spans."""
    global _tracer_provider
    if _tracer_provider:
        _tracer_provider.shutdown()
        _tracer_provider = None
        logger.info("OpenTelemetry tracing shutdown")
