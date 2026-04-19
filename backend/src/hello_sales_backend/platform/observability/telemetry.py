"""Tracing runtime built on OpenTelemetry."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from random import getrandbits
from typing import Any, Protocol

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
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

from hello_sales_backend.platform.llm import EffectivePromptRef


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
    agents_enabled: bool = False
    workers_enabled: bool = False
    otlp_endpoint: str = ""
    otlp_headers: dict[str, str] | None = None
    otlp_timeout_seconds: float = 10.0


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

    def start_agent_turn_span(
        self,
        *,
        run_id: str,
        turn_id: str,
        profile_name: str,
        prompt: EffectivePromptRef | None,
        request_id: str | None,
        trace_id: str | None,
    ) -> Any: ...

    def start_agent_tool_span(
        self,
        *,
        run_id: str,
        turn_id: str,
        tool_call_id: str,
        profile_name: str,
        tool_name: str,
        request_id: str | None,
        trace_id: str | None,
    ) -> Any: ...

    def start_worker_run_span(
        self,
        *,
        run_id: str,
        worker_name: str,
        prompt: EffectivePromptRef | None,
        request_id: str | None,
        trace_id: str | None,
        execution_mode: str,
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

    def finish_agent_turn_span(
        self,
        span: Span | None,
        *,
        run_id: str,
        turn_id: str,
        profile_name: str,
        status: str,
        error_type: str | None,
    ) -> None: ...

    def finish_agent_tool_span(
        self,
        span: Span | None,
        *,
        run_id: str,
        turn_id: str,
        tool_call_id: str,
        profile_name: str,
        tool_name: str,
        status: str,
        error_type: str | None,
    ) -> None: ...

    def finish_worker_run_span(
        self,
        span: Span | None,
        *,
        run_id: str,
        worker_name: str,
        status: str,
        error_type: str | None,
    ) -> None: ...

    def shutdown(self) -> None: ...

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

    @contextmanager
    def start_agent_turn_span(
        self,
        *,
        run_id: str,
        turn_id: str,
        profile_name: str,
        prompt: EffectivePromptRef | None,
        request_id: str | None,
        trace_id: str | None,
    ) -> Iterator[Span | None]:
        with nullcontext(None) as span:
            yield span

    @contextmanager
    def start_agent_tool_span(
        self,
        *,
        run_id: str,
        turn_id: str,
        tool_call_id: str,
        profile_name: str,
        tool_name: str,
        request_id: str | None,
        trace_id: str | None,
    ) -> Iterator[Span | None]:
        with nullcontext(None) as span:
            yield span

    @contextmanager
    def start_worker_run_span(
        self,
        *,
        run_id: str,
        worker_name: str,
        prompt: EffectivePromptRef | None,
        request_id: str | None,
        trace_id: str | None,
        execution_mode: str,
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

    def finish_agent_turn_span(
        self,
        span: Span | None,
        *,
        run_id: str,
        turn_id: str,
        profile_name: str,
        status: str,
        error_type: str | None,
    ) -> None:
        return None

    def finish_agent_tool_span(
        self,
        span: Span | None,
        *,
        run_id: str,
        turn_id: str,
        tool_call_id: str,
        profile_name: str,
        tool_name: str,
        status: str,
        error_type: str | None,
    ) -> None:
        return None

    def finish_worker_run_span(
        self,
        span: Span | None,
        *,
        run_id: str,
        worker_name: str,
        status: str,
        error_type: str | None,
    ) -> None:
        return None

    def shutdown(self) -> None:
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
        elif snapshot.exporter == "otlp":
            exporter = OTLPSpanExporter(
                endpoint=snapshot.otlp_endpoint,
                headers=snapshot.otlp_headers,
                timeout=snapshot.otlp_timeout_seconds,
            )
            self._provider.add_span_processor(BatchSpanProcessor(exporter))
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

    @contextmanager
    def start_agent_turn_span(
        self,
        *,
        run_id: str,
        turn_id: str,
        profile_name: str,
        prompt: EffectivePromptRef | None,
        request_id: str | None,
        trace_id: str | None,
    ) -> Iterator[Span | None]:
        if not self._snapshot.agents_enabled:
            with nullcontext(None) as span:
                yield span
            return
        attributes: dict[str, str] = {
            "hello_sales.agent_run_id": run_id,
            "hello_sales.agent_turn_id": turn_id,
            "hello_sales.agent_profile": profile_name,
        }
        attributes.update(_prompt_span_attributes(prompt))
        if request_id is not None:
            attributes["hello_sales.request_id"] = request_id
        if trace_id is not None:
            attributes["hello_sales.trace_id"] = trace_id
        with self._tracer.start_as_current_span(
            "agent_turn.execute",
            context=_parent_context(trace_id),
            attributes=attributes,
        ) as span:
            yield span

    @contextmanager
    def start_agent_tool_span(
        self,
        *,
        run_id: str,
        turn_id: str,
        tool_call_id: str,
        profile_name: str,
        tool_name: str,
        request_id: str | None,
        trace_id: str | None,
    ) -> Iterator[Span | None]:
        if not self._snapshot.agents_enabled:
            with nullcontext(None) as span:
                yield span
            return
        attributes: dict[str, str] = {
            "hello_sales.agent_run_id": run_id,
            "hello_sales.agent_turn_id": turn_id,
            "hello_sales.agent_tool_call_id": tool_call_id,
            "hello_sales.agent_profile": profile_name,
            "hello_sales.agent_tool_name": tool_name,
        }
        if request_id is not None:
            attributes["hello_sales.request_id"] = request_id
        if trace_id is not None:
            attributes["hello_sales.trace_id"] = trace_id
        with self._tracer.start_as_current_span(
            "agent_tool.execute",
            context=_parent_context(trace_id),
            attributes=attributes,
        ) as span:
            yield span

    @contextmanager
    def start_worker_run_span(
        self,
        *,
        run_id: str,
        worker_name: str,
        prompt: EffectivePromptRef | None,
        request_id: str | None,
        trace_id: str | None,
        execution_mode: str,
    ) -> Iterator[Span | None]:
        if not self._snapshot.workers_enabled:
            with nullcontext(None) as span:
                yield span
            return
        attributes: dict[str, str] = {
            "hello_sales.worker_run_id": run_id,
            "hello_sales.worker_name": worker_name,
            "hello_sales.worker_execution_mode": execution_mode,
        }
        attributes.update(_prompt_span_attributes(prompt))
        if request_id is not None:
            attributes["hello_sales.request_id"] = request_id
        if trace_id is not None:
            attributes["hello_sales.trace_id"] = trace_id
        with self._tracer.start_as_current_span(
            "worker_run.execute",
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
            span.set_status(
                Status(status_code=StatusCode.ERROR, description=error_type or str(status_code))
            )
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

    def finish_agent_turn_span(
        self,
        span: Span | None,
        *,
        run_id: str,
        turn_id: str,
        profile_name: str,
        status: str,
        error_type: str | None,
    ) -> None:
        if span is None:
            return
        span.set_attribute("hello_sales.agent_run_id", run_id)
        span.set_attribute("hello_sales.agent_turn_id", turn_id)
        span.set_attribute("hello_sales.agent_profile", profile_name)
        span.set_attribute("hello_sales.agent_turn_status", status)
        if error_type is not None:
            span.set_attribute("error.type", error_type)
            span.set_status(Status(status_code=StatusCode.ERROR, description=error_type))
            return
        span.set_status(Status(status_code=StatusCode.OK))

    def finish_agent_tool_span(
        self,
        span: Span | None,
        *,
        run_id: str,
        turn_id: str,
        tool_call_id: str,
        profile_name: str,
        tool_name: str,
        status: str,
        error_type: str | None,
    ) -> None:
        if span is None:
            return
        span.set_attribute("hello_sales.agent_run_id", run_id)
        span.set_attribute("hello_sales.agent_turn_id", turn_id)
        span.set_attribute("hello_sales.agent_tool_call_id", tool_call_id)
        span.set_attribute("hello_sales.agent_profile", profile_name)
        span.set_attribute("hello_sales.agent_tool_name", tool_name)
        span.set_attribute("hello_sales.agent_tool_status", status)
        if error_type is not None:
            span.set_attribute("error.type", error_type)
            span.set_status(Status(status_code=StatusCode.ERROR, description=error_type))
            return
        span.set_status(Status(status_code=StatusCode.OK))

    def finish_worker_run_span(
        self,
        span: Span | None,
        *,
        run_id: str,
        worker_name: str,
        status: str,
        error_type: str | None,
    ) -> None:
        if span is None:
            return
        span.set_attribute("hello_sales.worker_run_id", run_id)
        span.set_attribute("hello_sales.worker_name", worker_name)
        span.set_attribute("hello_sales.worker_status", status)
        if error_type is not None:
            span.set_attribute("error.type", error_type)
            span.set_status(Status(status_code=StatusCode.ERROR, description=error_type))
            return
        span.set_status(Status(status_code=StatusCode.OK))

    def shutdown(self) -> None:
        self._provider.shutdown()

    def snapshot(self) -> TracingRuntimeSnapshot:
        return self._snapshot


def _prompt_span_attributes(prompt: EffectivePromptRef | None) -> dict[str, str]:
    if prompt is None:
        return {}
    attributes = {
        "hello_sales.prompt_id": prompt.prompt_id,
        "hello_sales.prompt_version": prompt.version,
        "hello_sales.prompt_owner_kind": prompt.owner_kind,
        "hello_sales.prompt_owner_id": prompt.owner_id,
        "hello_sales.prompt_purpose": prompt.purpose,
    }
    if prompt.checksum is not None:
        attributes["hello_sales.prompt_checksum"] = prompt.checksum
    return attributes
