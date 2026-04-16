"""Prometheus-backed operational metrics runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

_HEALTHY_STATUSES = {"configured", "live", "missing", "ok", "ready"}
_FAILURE_TASK_STATUSES = {"cancelled", "failed", "partial_failure", "timed_out"}
_KNOWN_HEALTH_OVERALL_STATUSES: dict[str, tuple[str, ...]] = {
    "liveness": ("live",),
    "readiness": ("degraded", "not_ready", "ready"),
}


def _bool_label(value: bool) -> str:
    return "true" if value else "false"


@dataclass(frozen=True, slots=True)
class MetricsRuntimeSnapshot:
    """Operator-facing metrics runtime state."""

    enabled: bool
    exporter: str
    endpoint_enabled: bool
    endpoint_path: str
    http_enabled: bool
    health_enabled: bool
    background_tasks_enabled: bool


class MetricsRuntime(Protocol):
    """Operational metrics contract."""

    def render_latest(self) -> tuple[bytes, str]: ...

    def on_http_request_started(self) -> None: ...

    def on_http_request_finished(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        outcome: str,
        duration_seconds: float,
    ) -> None: ...

    def observe_health(
        self,
        *,
        kind: str,
        overall_status: str,
        checks: dict[str, tuple[str, bool]],
    ) -> None: ...

    def on_background_task_started(self, *, purpose: str) -> None: ...

    def on_background_task_finished(
        self,
        *,
        purpose: str,
        status: str,
        duration_seconds: float | None,
    ) -> None: ...

    def snapshot(self) -> MetricsRuntimeSnapshot: ...


class NoOpMetricsRuntime:
    """No-op metrics runtime used when metrics are disabled."""

    def __init__(self, snapshot: MetricsRuntimeSnapshot) -> None:
        self._snapshot = snapshot

    def render_latest(self) -> tuple[bytes, str]:
        return b"", CONTENT_TYPE_LATEST

    def on_http_request_started(self) -> None:
        return None

    def on_http_request_finished(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        outcome: str,
        duration_seconds: float,
    ) -> None:
        return None

    def observe_health(
        self,
        *,
        kind: str,
        overall_status: str,
        checks: dict[str, tuple[str, bool]],
    ) -> None:
        return None

    def on_background_task_started(self, *, purpose: str) -> None:
        return None

    def on_background_task_finished(
        self,
        *,
        purpose: str,
        status: str,
        duration_seconds: float | None,
    ) -> None:
        return None

    def snapshot(self) -> MetricsRuntimeSnapshot:
        return self._snapshot


class PrometheusMetricsRuntime:
    """Prometheus collector-backed runtime metrics."""

    def __init__(self, snapshot: MetricsRuntimeSnapshot) -> None:
        self._snapshot = snapshot
        self._registry = CollectorRegistry(auto_describe=True)
        self._http_active_requests = Gauge(
            "hello_sales_http_active_requests",
            "Number of in-flight HTTP requests.",
            registry=self._registry,
        )
        self._http_requests_total = Counter(
            "hello_sales_http_requests_total",
            "Total HTTP requests completed by route and outcome.",
            ["method", "route", "status_code", "outcome"],
            registry=self._registry,
        )
        self._http_request_duration_seconds = Histogram(
            "hello_sales_http_request_duration_seconds",
            "Duration of HTTP requests in seconds.",
            ["method", "route", "status_code", "outcome"],
            registry=self._registry,
        )
        self._health_overall_status = Gauge(
            "hello_sales_health_overall_status",
            "Health endpoint overall status; 1 indicates the current status label.",
            ["kind", "status"],
            registry=self._registry,
        )
        self._health_check_status = Gauge(
            "hello_sales_health_check_status",
            "Health check status; 1 indicates a healthy state.",
            ["kind", "check", "required"],
            registry=self._registry,
        )
        self._background_tasks_started_total = Counter(
            "hello_sales_background_tasks_started_total",
            "Total background tasks started.",
            ["purpose"],
            registry=self._registry,
        )
        self._background_tasks_completed_total = Counter(
            "hello_sales_background_tasks_completed_total",
            "Total background tasks completed by terminal status.",
            ["purpose", "status"],
            registry=self._registry,
        )
        self._background_tasks_failed_total = Counter(
            "hello_sales_background_tasks_failed_total",
            "Total background tasks ending in a failure-like terminal state.",
            ["purpose", "status"],
            registry=self._registry,
        )
        self._background_tasks_active = Gauge(
            "hello_sales_background_tasks_active",
            "Number of active background tasks by purpose.",
            ["purpose"],
            registry=self._registry,
        )
        self._background_task_duration_seconds = Histogram(
            "hello_sales_background_task_duration_seconds",
            "Duration of background tasks in seconds.",
            ["purpose", "status"],
            registry=self._registry,
        )

    def render_latest(self) -> tuple[bytes, str]:
        return generate_latest(self._registry), CONTENT_TYPE_LATEST

    def on_http_request_started(self) -> None:
        if not self._snapshot.http_enabled:
            return
        self._http_active_requests.inc()

    def on_http_request_finished(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        outcome: str,
        duration_seconds: float,
    ) -> None:
        if not self._snapshot.http_enabled:
            return
        self._http_active_requests.dec()
        labels = {
            "method": method,
            "route": route,
            "status_code": str(status_code),
            "outcome": outcome,
        }
        self._http_requests_total.labels(**labels).inc()
        self._http_request_duration_seconds.labels(**labels).observe(duration_seconds)

    def observe_health(
        self,
        *,
        kind: str,
        overall_status: str,
        checks: dict[str, tuple[str, bool]],
    ) -> None:
        if not self._snapshot.health_enabled:
            return
        for known_status in _KNOWN_HEALTH_OVERALL_STATUSES.get(kind, (overall_status,)):
            self._health_overall_status.labels(kind=kind, status=known_status).set(
                1 if known_status == overall_status else 0
            )
        for check_name, (status, required) in checks.items():
            self._health_check_status.labels(
                kind=kind,
                check=check_name,
                required=_bool_label(required),
            ).set(1 if status in _HEALTHY_STATUSES else 0)

    def on_background_task_started(self, *, purpose: str) -> None:
        if not self._snapshot.background_tasks_enabled:
            return
        self._background_tasks_started_total.labels(purpose=purpose).inc()
        self._background_tasks_active.labels(purpose=purpose).inc()

    def on_background_task_finished(
        self,
        *,
        purpose: str,
        status: str,
        duration_seconds: float | None,
    ) -> None:
        if not self._snapshot.background_tasks_enabled:
            return
        self._background_tasks_active.labels(purpose=purpose).dec()
        self._background_tasks_completed_total.labels(purpose=purpose, status=status).inc()
        if status in _FAILURE_TASK_STATUSES:
            self._background_tasks_failed_total.labels(purpose=purpose, status=status).inc()
        if duration_seconds is not None:
            self._background_task_duration_seconds.labels(purpose=purpose, status=status).observe(
                duration_seconds
            )

    def snapshot(self) -> MetricsRuntimeSnapshot:
        return self._snapshot
