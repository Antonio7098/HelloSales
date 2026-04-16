"""System use-case ports."""

from __future__ import annotations

from typing import Protocol

from hello_sales_backend.platform.agents.models import AgentDiagnosticsSummary
from hello_sales_backend.platform.observability.events import OperationalEvent
from hello_sales_backend.platform.observability.runtime import (
    AlertRecord,
    ObservabilityDiagnosticsSnapshot,
)


class ClockPort(Protocol):
    """Provides UTC timestamps for runtime status."""

    def now_iso(self) -> str: ...


class ObservabilityPort(Protocol):
    """Provides operational event and alert diagnostics."""

    def recent_events(self, limit: int = 20) -> list[OperationalEvent]: ...

    def active_alerts(self, limit: int = 20) -> list[AlertRecord]: ...

    def diagnostics(self) -> ObservabilityDiagnosticsSnapshot: ...


class AgentDiagnosticsPort(Protocol):
    """Provides operator-facing agent run diagnostics."""

    async def summarize(self, limit: int = 10) -> AgentDiagnosticsSummary: ...


class AgentRegistryPort(Protocol):
    """Provides registered agent profile metadata."""

    def list_profiles(self) -> list[tuple[str, str]]: ...
