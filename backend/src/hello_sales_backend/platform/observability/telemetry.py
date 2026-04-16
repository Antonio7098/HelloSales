"""Tracing runtime built on OpenTelemetry."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from random import getrandbits
from typing import Any, Protocol

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.trace import (
    NonRecordingSpan,
    Span,
    SpanContext,
    Status,
    StatusCode,
    TraceFlags,
    TraceState,
    set_span_in_context,
)


def _is_valid_hex_trace_id(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    if len(normalized) != 32:
        return False
    try:
        return int(normalized, 16) != 0
    except ValueError:
        return False


def _parent_context(trace_id: str | None) -> Any | None:
    if trace_id is None or not _is_valid_hex_trace_id(trace_id):
        return None
    normalized_trace_id = trace_id.strip().lower()
    span_context = SpanContext(
        trace_id=int(normalized_trace_id, 16),
        span_id=getrandbits(64),
        is_remote=False,
        trace_flags=TraceFlags(0x01),
        trace_state=TraceState(),
    )
    return set_span_in_context(NonRecordingSpan(span_context))


@dataclass(frozen=True, slots=True)
class TracingRuntimeSnapshot:
    """Operator-facing tracing runtime state."""

    enabled: bool
    exporter: str
    service_name: str
    service_version: str
    environment: str
    http_enabled: bool
    background_tasks_enabled: bool


class TracingRuntime(Protocol):
    """Tracing contract used by HTTP and background task boundaries."""

    def start_http_span(
        self,
        *,
        method: str,
        path: str,
        request_id: str | None,
        trace_id: str | None,
    ) -> Any: ...

    def start_background_task_span(
        self,
        *,
        task_id: str,
        purpose: str,
        request_id: str | None,
        trace_id: str | None,
    ) -> Any: ...

    def finish_http_span(
        self,
        span: Span | None,
        *,
        route: str,
        status_code: int,
        error_type: str | None,
    ) -> None: ...

    def finish_background_task_span(
        self,
        span: Span | None,
        *,
        task_id: str,
        purpose: str,
        status: str,
        error_type: str | None,
    ) -> None: ...

    def snapshot(self) -> TracingRuntimeSnapshot: ...


class NoOpTracingRuntime:
    """No-op tracing runtime used when tracing is disabled."""

    def __init__(self, snapshot: TracingRuntimeSnapshot) -> None:
        self._snapshot = snapshot

    @contextmanager
    def start_http_span(
        self,
        *,
        method: str,
        path: str,
        request_id: str | None,
        trace_id: str | None,
    ) -> Iterator[Span | None]:
        with nullcontext(None) as span:
            yield span

    @contextmanager
    def start_background_task_span(
        self,
        *,
        task_id: str,
        purpose: str,
        request_id: str | None,
        trace_id: str | None,
    ) -> Iterator[Span | None]:
        with nullcontext(None) as span:
            yield span

    def finish_http_span(
        self,
        span: Span | None,
        *,
        route: str,
        status_code: int,
        error_type: str | None,
    ) -> None:
        return None

    def finish_background_task_span(
        self,
        span: Span | None,
        *,
        task_id: str,
        purpose: str,
        status: str,
        error_type: str | None,
    ) -> None:
        return None

    def snapshot(self) -> TracingRuntimeSnapshot:
        return self._snapshot


class OpenTelemetryTracingRuntime:
    """OpenTelemetry tracer provider with optional console export."""

    def __init__(self, snapshot: TracingRuntimeSnapshot) -> None:
        self._snapshot = snapshot
        resource = Resource.create(
            {
                "service.name": snapshot.service_name,
                "service.version": snapshot.service_version,
                "deployment.environment": snapshot.environment,
            }
        )
        self._provider = TracerProvider(resource=resource)
        if snapshot.exporter == "console":
            self._provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        self._tracer = self._provider.get_tracer("hello_sales_backend.observability")

    @contextmanager
    def start_http_span(
        self,
        *,
        method: str,
        path: str,
        request_id: str | None,
        trace_id: str | None,
    ) -> Iterator[Span | None]:
        if not self._snapshot.http_enabled:
            with nullcontext(None) as span:
                yield span
            return
        attributes: dict[str, str] = {
            "http.request.method": method,
            "url.path": path,
        }
        if request_id is not None:
            attributes["hello_sales.request_id"] = request_id
        if trace_id is not None:
            attributes["hello_sales.trace_id"] = trace_id
        with self._tracer.start_as_current_span(
            "http.request",
            context=_parent_context(trace_id),
            attributes=attributes,
        ) as span:
            yield span

    @contextmanager
    def start_background_task_span(
        self,
        *,
        task_id: str,
        purpose: str,
        request_id: str | None,
        trace_id: str | None,
    ) -> Iterator[Span | None]:
        if not self._snapshot.background_tasks_enabled:
            with nullcontext(None) as span:
                yield span
            return
        attributes: dict[str, str] = {
            "hello_sales.task_id": task_id,
            "hello_sales.task_purpose": purpose,
        }
        if request_id is not None:
            attributes["hello_sales.request_id"] = request_id
        if trace_id is not None:
            attributes["hello_sales.trace_id"] = trace_id
        with self._tracer.start_as_current_span(
            "background_task.execute",
            context=_parent_context(trace_id),
            attributes=attributes,
        ) as span:
            yield span

    def finish_http_span(
        self,
        span: Span | None,
        *,
        route: str,
        status_code: int,
        error_type: str | None,
    ) -> None:
        if span is None:
            return
        span.set_attribute("http.route", route)
        span.set_attribute("http.response.status_code", status_code)
        if error_type is not None or status_code >= 500:
            span.set_status(Status(status_code=StatusCode.ERROR, description=error_type or str(status_code)))
            if error_type is not None:
                span.set_attribute("error.type", error_type)
            return
        span.set_status(Status(status_code=StatusCode.OK))

    def finish_background_task_span(
        self,
        span: Span | None,
        *,
        task_id: str,
        purpose: str,
        status: str,
        error_type: str | None,
    ) -> None:
        if span is None:
            return
        span.set_attribute("hello_sales.task_id", task_id)
        span.set_attribute("hello_sales.task_purpose", purpose)
        span.set_attribute("hello_sales.task_status", status)
        if error_type is not None:
            span.set_attribute("error.type", error_type)
            span.set_status(Status(status_code=StatusCode.ERROR, description=error_type))
            return
        span.set_status(Status(status_code=StatusCode.OK))

    def snapshot(self) -> TracingRuntimeSnapshot:
        return self._snapshot
