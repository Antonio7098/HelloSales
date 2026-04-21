"""Prometheus-backed operational metrics runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )
except ImportError:  # pragma: no cover - exercised only in dependency-light environments
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    class CollectorRegistry:  # type: ignore[no-redef]
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.metrics: list[_MetricBase] = []

        def register(self, metric: _MetricBase) -> None:
            self.metrics.append(metric)

    class _MetricHandle:
        def __init__(self, metric: _MetricBase, values: tuple[str, ...]) -> None:
            self._metric = metric
            self._values = values

        def inc(self, amount: float = 1) -> None:
            self._metric.inc(amount, label_values=self._values)

        def dec(self, amount: float = 1) -> None:
            self._metric.dec(amount, label_values=self._values)

        def observe(self, value: float) -> None:
            self._metric.observe(value, label_values=self._values)

        def set(self, value: float) -> None:
            self._metric.set(value, label_values=self._values)

    class _MetricBase:
        metric_type = "gauge"

        def __init__(
            self,
            name: str,
            documentation: str,
            labelnames: list[str] | tuple[str, ...] | None = None,
            *,
            registry: CollectorRegistry,
        ) -> None:
            self._name = name
            self._documentation = documentation
            self._labelnames = tuple(labelnames or ())
            self._samples: dict[tuple[str, ...], float] = {}
            registry.register(self)

        def labels(self, **labels: object) -> _MetricHandle:
            label_values = tuple(str(labels[name]) for name in self._labelnames)
            return _MetricHandle(self, label_values)

        def inc(self, amount: float = 1, *, label_values: tuple[str, ...] = ()) -> None:
            self._samples[label_values] = self._samples.get(label_values, 0.0) + float(amount)

        def dec(self, amount: float = 1, *, label_values: tuple[str, ...] = ()) -> None:
            self._samples[label_values] = self._samples.get(label_values, 0.0) - float(amount)

        def observe(self, value: float, *, label_values: tuple[str, ...] = ()) -> None:
            self.inc(value, label_values=label_values)

        def set(self, value: float, *, label_values: tuple[str, ...] = ()) -> None:
            self._samples[label_values] = float(value)

        def render(self) -> list[str]:
            lines = [f"# HELP {self._name} {self._documentation}", f"# TYPE {self._name} {self.metric_type}"]
            for label_values, value in sorted(self._samples.items()):
                lines.append(f"{self._name}{self._format_labels(label_values)} {value}")
            return lines

        def _format_labels(self, label_values: tuple[str, ...]) -> str:
            if not self._labelnames:
                return ""
            pairs = sorted(zip(self._labelnames, label_values, strict=False), key=lambda item: item[0])
            rendered = ",".join(f'{name}="{value}"' for name, value in pairs)
            return f"{{{rendered}}}"

    class Counter(_MetricBase):  # type: ignore[no-redef]
        metric_type = "counter"

    class Gauge(_MetricBase):  # type: ignore[no-redef]
        metric_type = "gauge"

    class Histogram(_MetricBase):  # type: ignore[no-redef]
        metric_type = "histogram"

        def __init__(
            self,
            name: str,
            documentation: str,
            labelnames: list[str] | tuple[str, ...] | None = None,
            *,
            registry: CollectorRegistry,
        ) -> None:
            super().__init__(name, documentation, labelnames, registry=registry)
            self._counts: dict[tuple[str, ...], float] = {}

        def observe(self, value: float, *, label_values: tuple[str, ...] = ()) -> None:
            self._samples[label_values] = self._samples.get(label_values, 0.0) + float(value)
            self._counts[label_values] = self._counts.get(label_values, 0.0) + 1.0

        def render(self) -> list[str]:
            lines = [f"# HELP {self._name} {self._documentation}", f"# TYPE {self._name} {self.metric_type}"]
            for label_values in sorted(self._samples):
                label_suffix = self._format_labels(label_values)
                lines.append(f"{self._name}_sum{label_suffix} {self._samples[label_values]}")
                lines.append(f"{self._name}_count{label_suffix} {self._counts.get(label_values, 0.0)}")
            return lines

    def generate_latest(registry: CollectorRegistry) -> bytes:
        rendered_lines: list[str] = []
        for metric in registry.metrics:
            rendered_lines.extend(metric.render())
        if rendered_lines:
            rendered_lines.append("")
        return "\n".join(rendered_lines).encode("utf-8")

from hello_sales_backend.platform.tasks.models import TaskStatus

_HEALTHY_STATUSES = {"configured", "live", "missing", "ok", "ready"}
_FAILURE_TASK_STATUSES = {
    TaskStatus.CANCELLED.value,
    TaskStatus.FAILED.value,
    TaskStatus.PARTIAL_FAILURE.value,
    TaskStatus.TIMED_OUT.value,
}
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
    agents_enabled: bool = False
    workers_enabled: bool = False


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

    def on_agent_turn_execution_started(self, *, profile_name: str) -> None: ...

    def on_agent_turn_execution_finished(
        self,
        *,
        profile_name: str,
        status: str,
        duration_seconds: float | None,
    ) -> None: ...

    def on_agent_tool_approval_requested(self, *, profile_name: str, tool_name: str) -> None: ...

    def on_agent_tool_call_started(self, *, profile_name: str, tool_name: str) -> None: ...

    def on_agent_tool_call_finished(
        self,
        *,
        profile_name: str,
        tool_name: str,
        status: str,
        duration_seconds: float | None,
    ) -> None: ...

    def on_worker_run_started(self, *, worker_name: str, execution_mode: str) -> None: ...

    def on_worker_run_finished(
        self,
        *,
        worker_name: str,
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

    def on_agent_turn_execution_started(self, *, profile_name: str) -> None:
        return None

    def on_agent_turn_execution_finished(
        self,
        *,
        profile_name: str,
        status: str,
        duration_seconds: float | None,
    ) -> None:
        return None

    def on_agent_tool_approval_requested(self, *, profile_name: str, tool_name: str) -> None:
        return None

    def on_agent_tool_call_started(self, *, profile_name: str, tool_name: str) -> None:
        return None

    def on_agent_tool_call_finished(
        self,
        *,
        profile_name: str,
        tool_name: str,
        status: str,
        duration_seconds: float | None,
    ) -> None:
        return None

    def on_worker_run_started(self, *, worker_name: str, execution_mode: str) -> None:
        return None

    def on_worker_run_finished(
        self,
        *,
        worker_name: str,
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
        self._agent_turn_executions_started_total = Counter(
            "hello_sales_agent_turn_executions_started_total",
            "Total agent turn execution segments started.",
            ["profile"],
            registry=self._registry,
        )
        self._agent_turn_executions_completed_total = Counter(
            "hello_sales_agent_turn_executions_completed_total",
            "Total agent turn execution segments completed by terminal status.",
            ["profile", "status"],
            registry=self._registry,
        )
        self._agent_turn_executions_active = Gauge(
            "hello_sales_agent_turn_executions_active",
            "Number of active agent turn execution segments by profile.",
            ["profile"],
            registry=self._registry,
        )
        self._agent_turn_execution_duration_seconds = Histogram(
            "hello_sales_agent_turn_execution_duration_seconds",
            "Duration of agent turn execution segments in seconds.",
            ["profile", "status"],
            registry=self._registry,
        )
        self._agent_tool_approval_requests_total = Counter(
            "hello_sales_agent_tool_approval_requests_total",
            "Total agent tool approval requests raised.",
            ["profile", "tool"],
            registry=self._registry,
        )
        self._agent_tool_calls_started_total = Counter(
            "hello_sales_agent_tool_calls_started_total",
            "Total agent tool calls started.",
            ["profile", "tool"],
            registry=self._registry,
        )
        self._agent_tool_calls_completed_total = Counter(
            "hello_sales_agent_tool_calls_completed_total",
            "Total agent tool calls completed by terminal status.",
            ["profile", "tool", "status"],
            registry=self._registry,
        )
        self._agent_tool_call_duration_seconds = Histogram(
            "hello_sales_agent_tool_call_duration_seconds",
            "Duration of agent tool calls in seconds.",
            ["profile", "tool", "status"],
            registry=self._registry,
        )
        self._worker_runs_started_total = Counter(
            "hello_sales_worker_runs_started_total",
            "Total worker runs started.",
            ["worker", "execution_mode"],
            registry=self._registry,
        )
        self._worker_runs_completed_total = Counter(
            "hello_sales_worker_runs_completed_total",
            "Total worker runs completed by terminal status.",
            ["worker", "status"],
            registry=self._registry,
        )
        self._worker_runs_active = Gauge(
            "hello_sales_worker_runs_active",
            "Number of active worker runs by worker name.",
            ["worker"],
            registry=self._registry,
        )
        self._worker_run_duration_seconds = Histogram(
            "hello_sales_worker_run_duration_seconds",
            "Duration of worker runs in seconds.",
            ["worker", "status"],
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

    def on_agent_turn_execution_started(self, *, profile_name: str) -> None:
        if not self._snapshot.agents_enabled:
            return
        self._agent_turn_executions_started_total.labels(profile=profile_name).inc()
        self._agent_turn_executions_active.labels(profile=profile_name).inc()

    def on_agent_turn_execution_finished(
        self,
        *,
        profile_name: str,
        status: str,
        duration_seconds: float | None,
    ) -> None:
        if not self._snapshot.agents_enabled:
            return
        self._agent_turn_executions_active.labels(profile=profile_name).dec()
        self._agent_turn_executions_completed_total.labels(
            profile=profile_name, status=status
        ).inc()
        if duration_seconds is not None:
            self._agent_turn_execution_duration_seconds.labels(
                profile=profile_name, status=status
            ).observe(duration_seconds)

    def on_agent_tool_approval_requested(self, *, profile_name: str, tool_name: str) -> None:
        if not self._snapshot.agents_enabled:
            return
        self._agent_tool_approval_requests_total.labels(profile=profile_name, tool=tool_name).inc()

    def on_agent_tool_call_started(self, *, profile_name: str, tool_name: str) -> None:
        if not self._snapshot.agents_enabled:
            return
        self._agent_tool_calls_started_total.labels(profile=profile_name, tool=tool_name).inc()

    def on_agent_tool_call_finished(
        self,
        *,
        profile_name: str,
        tool_name: str,
        status: str,
        duration_seconds: float | None,
    ) -> None:
        if not self._snapshot.agents_enabled:
            return
        self._agent_tool_calls_completed_total.labels(
            profile=profile_name, tool=tool_name, status=status
        ).inc()
        if duration_seconds is not None:
            self._agent_tool_call_duration_seconds.labels(
                profile=profile_name, tool=tool_name, status=status
            ).observe(duration_seconds)

    def on_worker_run_started(self, *, worker_name: str, execution_mode: str) -> None:
        if not self._snapshot.workers_enabled:
            return
        self._worker_runs_started_total.labels(
            worker=worker_name, execution_mode=execution_mode
        ).inc()
        self._worker_runs_active.labels(worker=worker_name).inc()

    def on_worker_run_finished(
        self,
        *,
        worker_name: str,
        status: str,
        duration_seconds: float | None,
    ) -> None:
        if not self._snapshot.workers_enabled:
            return
        self._worker_runs_active.labels(worker=worker_name).dec()
        self._worker_runs_completed_total.labels(worker=worker_name, status=status).inc()
        if duration_seconds is not None:
            self._worker_run_duration_seconds.labels(worker=worker_name, status=status).observe(
                duration_seconds
            )

    def snapshot(self) -> MetricsRuntimeSnapshot:
        return self._snapshot
