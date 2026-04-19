"""Worker persistence contracts."""

from __future__ import annotations

from typing import Protocol

from hello_sales_backend.platform.workers.models import (
    WorkerDiagnosticsSummary,
    WorkerRun,
    WorkerRunEvent,
)


class WorkerStorePort(Protocol):
    """Persist and query worker run state."""

    async def create_run(self, run: WorkerRun) -> None: ...

    async def get_run(self, run_id: str) -> WorkerRun | None: ...

    async def update_run(self, run: WorkerRun) -> None: ...

    async def append_event(self, event: WorkerRunEvent) -> None: ...

    async def list_events(self, run_id: str, limit: int = 100) -> list[WorkerRunEvent]: ...

    async def next_event_sequence(self, run_id: str) -> int: ...

    async def summarize(self, limit: int = 10) -> WorkerDiagnosticsSummary: ...
