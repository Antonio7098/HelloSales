"""Operational events, metrics, and tracing runtime."""

from __future__ import annotations

from collections import deque
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, cast

from opentelemetry.trace import Span

from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.observability.events import OperationalEvent
from hello_sales_backend.platform.observability.metrics import (
    MetricsRuntime,
    MetricsRuntimeSnapshot,
    NoOpMetricsRuntime,
    PrometheusMetricsRuntime,
)
from hello_sales_backend.platform.observability.telemetry import (
    NoOpTracingRuntime,
    OpenTelemetryTracingRuntime,
    TracingRuntime,
    TracingRuntimeSnapshot,
)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class AlertRecord:
    """Raised operational alert."""

    code: str
    severity: str
    message: str
    created_at: str = field(default_factory=_utc_now_iso)
    event_type: str | None = None
    component: str | None = None
    operation: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ObservabilityDiagnosticsSnapshot:
    """Operator-facing observability runtime state."""

    metrics: MetricsRuntimeSnapshot
    tracing: TracingRuntimeSnapshot


class OperationalEventSink(Protocol):
    """Durable sink for operational events."""

    async def emit(self, event: OperationalEvent) -> None: ...


class InMemoryOperationalStore(OperationalEventSink):
    """Small in-memory event and alert store for scaffold-stage visibility."""

    def __init__(self, max_events: int = 200, max_alerts: int = 100) -> None:
        self._events: deque[OperationalEvent] = deque(maxlen=max_events)
        self._alerts: deque[AlertRecord] = deque(maxlen=max_alerts)

    async def emit(self, event: OperationalEvent) -> None:
        self._events.appendleft(event)

    def add_alert(self, alert: AlertRecord) -> None:
        self._alerts.appendleft(alert)

    def recent_events(self, limit: int = 20) -> list[OperationalEvent]:
        return list(self._events)[:limit]

    def active_alerts(self, limit: int = 20) -> list[AlertRecord]:
        return list(self._alerts)[:limit]


class AlertPolicy:
    """Minimal alerting rules for scaffold-stage operations."""

    def evaluate(self, event: OperationalEvent) -> AlertRecord | None:
        payload = event.payload
        severity = str(payload.get("severity", event.severity))
        code = str(payload.get("code", "event.unknown"))
        if severity not in {"error", "critical"}:
            return None
        return AlertRecord(
            code=code,
            severity=severity,
            message=str(payload.get("message", event.event_type)),
            event_type=event.event_type,
            component=event.component,
            operation=event.operation,
            correlation_id=event.correlation_id,
            trace_id=event.trace_id,
            details=payload,
        )


@dataclass(slots=True)
class ObservabilityRuntime:
    """Owns operational event emission, metrics, and tracing."""

    store: InMemoryOperationalStore
    alert_policy: AlertPolicy
    metrics: MetricsRuntime = field(default_factory=lambda: NoOpMetricsRuntime(_default_metrics_snapshot()))
    tracing: TracingRuntime = field(default_factory=lambda: NoOpTracingRuntime(_default_tracing_snapshot()))

    async def emit(self, event: OperationalEvent) -> None:
        await self.store.emit(event)
        alert = self.alert_policy.evaluate(event)
        if alert is not None:
            self.store.add_alert(alert)

    def recent_events(self, limit: int = 20) -> list[OperationalEvent]:
        return self.store.recent_events(limit)

    def active_alerts(self, limit: int = 20) -> list[AlertRecord]:
        return self.store.active_alerts(limit)

    def render_metrics(self) -> tuple[bytes, str]:
        return self.metrics.render_latest()

    def diagnostics(self) -> ObservabilityDiagnosticsSnapshot:
        return ObservabilityDiagnosticsSnapshot(
            metrics=self.metrics.snapshot(),
            tracing=self.tracing.snapshot(),
        )

    def on_http_request_started(self) -> None:
        self.metrics.on_http_request_started()

    def on_http_request_finished(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        outcome: str,
        duration_seconds: float,
    ) -> None:
        self.metrics.on_http_request_finished(
            method=method,
            route=route,
            status_code=status_code,
            outcome=outcome,
            duration_seconds=duration_seconds,
        )

    def observe_health(
        self,
        *,
        kind: str,
        overall_status: str,
        checks: dict[str, tuple[str, bool]],
    ) -> None:
        self.metrics.observe_health(kind=kind, overall_status=overall_status, checks=checks)

    def start_http_span(
        self,
        *,
        method: str,
        path: str,
        request_id: str | None,
        trace_id: str | None,
    ) -> AbstractContextManager[Span | None]:
        return cast(
            AbstractContextManager[Span | None],
            self.tracing.start_http_span(
                method=method,
                path=path,
                request_id=request_id,
                trace_id=trace_id,
            ),
        )

    def finish_http_span(
        self,
        span: Span | None,
        *,
        route: str,
        status_code: int,
        error_type: str | None,
    ) -> None:
        self.tracing.finish_http_span(
            span,
            route=route,
            status_code=status_code,
            error_type=error_type,
        )

    def start_background_task_span(
        self,
        *,
        task_id: str,
        purpose: str,
        request_id: str | None,
        trace_id: str | None,
    ) -> AbstractContextManager[Span | None]:
        return cast(
            AbstractContextManager[Span | None],
            self.tracing.start_background_task_span(
                task_id=task_id,
                purpose=purpose,
                request_id=request_id,
                trace_id=trace_id,
            ),
        )

    def finish_background_task_span(
        self,
        span: Span | None,
        *,
        task_id: str,
        purpose: str,
        status: str,
        error_type: str | None,
    ) -> None:
        self.tracing.finish_background_task_span(
            span,
            task_id=task_id,
            purpose=purpose,
            status=status,
            error_type=error_type,
        )


def _default_metrics_snapshot() -> MetricsRuntimeSnapshot:
    return MetricsRuntimeSnapshot(
        enabled=False,
        exporter="prometheus",
        endpoint_enabled=False,
        endpoint_path="/metrics",
        http_enabled=False,
        health_enabled=False,
        background_tasks_enabled=False,
    )


def _default_tracing_snapshot() -> TracingRuntimeSnapshot:
    return TracingRuntimeSnapshot(
        enabled=False,
        exporter="none",
        service_name="hello-sales-backend",
        service_version="0.1.0",
        environment="development",
        http_enabled=False,
        background_tasks_enabled=False,
    )


def build_metrics_runtime(settings: Settings) -> MetricsRuntime:
    """Build the configured metrics runtime."""

    snapshot = MetricsRuntimeSnapshot(
        enabled=settings.observability_metrics_enabled,
        exporter=settings.observability_metrics_exporter,
        endpoint_enabled=settings.observability_metrics_endpoint_enabled,
        endpoint_path=settings.observability_metrics_endpoint_path,
        http_enabled=settings.observability_metrics_http_enabled,
        health_enabled=settings.observability_metrics_health_enabled,
        background_tasks_enabled=settings.observability_metrics_background_tasks_enabled,
    )
    if not settings.observability_metrics_enabled:
        return NoOpMetricsRuntime(snapshot)
    return PrometheusMetricsRuntime(snapshot)


def build_tracing_runtime(settings: Settings) -> TracingRuntime:
    """Build the configured tracing runtime."""

    snapshot = TracingRuntimeSnapshot(
        enabled=settings.observability_tracing_enabled,
        exporter=settings.observability_tracing_exporter,
        service_name=settings.resolved_observability_service_name,
        service_version=settings.resolved_observability_service_version,
        environment=settings.environment,
        http_enabled=settings.observability_tracing_http_enabled,
        background_tasks_enabled=settings.observability_tracing_background_tasks_enabled,
    )
    if not settings.observability_tracing_enabled:
        return NoOpTracingRuntime(snapshot)
    return OpenTelemetryTracingRuntime(snapshot)
