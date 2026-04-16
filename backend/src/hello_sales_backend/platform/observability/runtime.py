"""Operational event and alert runtime."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from hello_sales_backend.platform.observability.events import OperationalEvent


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
    """Owns operational event emission and alert derivation."""

    store: InMemoryOperationalStore
    alert_policy: AlertPolicy

    async def emit(self, event: OperationalEvent) -> None:
        await self.store.emit(event)
        alert = self.alert_policy.evaluate(event)
        if alert is not None:
            self.store.add_alert(alert)

    def recent_events(self, limit: int = 20) -> list[OperationalEvent]:
        return self.store.recent_events(limit)

    def active_alerts(self, limit: int = 20) -> list[AlertRecord]:
        return self.store.active_alerts(limit)
