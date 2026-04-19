"""In-memory worker persistence."""

from __future__ import annotations

from hello_sales_backend.platform.workers.models import (
    WorkerDiagnosticsSummary,
    WorkerRun,
    WorkerRunEvent,
    WorkerRunStatus,
)


class InMemoryWorkerStore:
    """Persist worker state in memory for local and sqlite-backed execution."""

    def __init__(self) -> None:
        self._runs: dict[str, WorkerRun] = {}
        self._events: dict[str, list[WorkerRunEvent]] = {}

    async def create_run(self, run: WorkerRun) -> None:
        self._runs[run.run_id] = run

    async def get_run(self, run_id: str) -> WorkerRun | None:
        return self._runs.get(run_id)

    async def update_run(self, run: WorkerRun) -> None:
        self._runs[run.run_id] = run

    async def append_event(self, event: WorkerRunEvent) -> None:
        events = self._events.setdefault(event.run_id, [])
        events.append(event)
        events.sort(key=lambda item: item.sequence_no)

    async def list_events(self, run_id: str, limit: int = 100) -> list[WorkerRunEvent]:
        return list(self._events.get(run_id, []))[:limit]

    async def next_event_sequence(self, run_id: str) -> int:
        return len(self._events.get(run_id, [])) + 1

    async def summarize(self, limit: int = 10) -> WorkerDiagnosticsSummary:
        recent_runs = sorted(self._runs.values(), key=lambda item: item.created_at, reverse=True)
        active_count = sum(
            1 for item in self._runs.values() if item.status in {WorkerRunStatus.RUNNING, WorkerRunStatus.RETRYING}
        )
        return WorkerDiagnosticsSummary(
            active_count=active_count,
            total_count=len(self._runs),
            recent_runs=recent_runs[:limit],
        )
