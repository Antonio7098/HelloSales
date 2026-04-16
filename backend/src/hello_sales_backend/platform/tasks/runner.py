"""Application-scoped background task runner."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any

from hello_sales_backend.platform.observability.logging import get_logger
from hello_sales_backend.platform.observability.events import OperationalEvent
from hello_sales_backend.platform.observability.runtime import ObservabilityRuntime
from hello_sales_backend.platform.tasks.models import TaskEventSink, TaskMetadata, TaskSnapshot, TaskStatus, utc_now
from hello_sales_backend.shared.errors import AppError, normalize_details


@dataclass(slots=True)
class TaskFailure:
    """Recorded background task failure."""

    metadata: TaskMetadata
    error_type: str
    message: str
    code: str | None = None
    category: str | None = None
    details: dict[str, object] | None = None


class BackgroundTaskRunner:
    """Schedule and observe application-scoped background tasks."""

    def __init__(
        self,
        event_sink: TaskEventSink | None = None,
        observability: ObservabilityRuntime | None = None,
    ) -> None:
        self._logger = get_logger("hello_sales_backend.tasks")
        self._tasks: dict[asyncio.Task[Any], str] = {}
        self._snapshots: dict[str, TaskSnapshot] = {}
        self._failures: list[TaskFailure] = []
        self._event_sink = event_sink
        self._observability = observability

    def start(self, metadata: TaskMetadata, coro: Coroutine[Any, Any, Any]) -> str:
        snapshot = TaskSnapshot(
            metadata=metadata,
            status=TaskStatus.RUNNING,
            created_at=utc_now(),
            started_at=utc_now(),
        )
        self._snapshots[metadata.task_id] = snapshot
        self._emit_snapshot(snapshot)
        task = asyncio.create_task(coro)
        self._tasks[task] = metadata.task_id
        task.add_done_callback(self._handle_task_done)
        return metadata.task_id

    async def shutdown(self) -> None:
        tasks = list(self._tasks.keys())
        if not tasks:
            return
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

    def pop_failures(self) -> list[TaskFailure]:
        failures = list(self._failures)
        self._failures.clear()
        return failures

    def cancel(self, task_id: str) -> bool:
        for task, recorded_task_id in list(self._tasks.items()):
            if recorded_task_id == task_id:
                task.cancel()
                return True
        return False

    def list_snapshots(self, *, limit: int | None = None) -> list[TaskSnapshot]:
        snapshots = sorted(
            self._snapshots.values(),
            key=lambda item: item.created_at,
            reverse=True,
        )
        return snapshots if limit is None else snapshots[:limit]

    def active_count(self) -> int:
        return sum(1 for snapshot in self._snapshots.values() if snapshot.status == TaskStatus.RUNNING)

    def failure_count(self) -> int:
        return sum(
            1
            for snapshot in self._snapshots.values()
            if snapshot.status in {TaskStatus.FAILED, TaskStatus.TIMED_OUT, TaskStatus.PARTIAL_FAILURE}
        )

    def _handle_task_done(self, task: asyncio.Task[Any]) -> None:
        task_id = self._tasks.pop(task, None)
        try:
            exception = task.exception()
        except asyncio.CancelledError:
            if task_id is not None:
                snapshot = self._snapshots[task_id]
                snapshot.status = TaskStatus.CANCELLED
                snapshot.finished_at = utc_now()
                self._emit_snapshot(snapshot)
            return
        if task_id is None:
            return
        snapshot = self._snapshots[task_id]
        snapshot.finished_at = utc_now()
        if exception is None:
            snapshot.status = TaskStatus.COMPLETED
            self._emit_snapshot(snapshot)
            return
        snapshot.status = TaskStatus.FAILED
        snapshot.error_type = exception.__class__.__name__
        snapshot.error_message = str(exception)
        if isinstance(exception, AppError):
            snapshot.error_code = exception.code
            snapshot.error_category = exception.category
            snapshot.error_details = exception.to_dict()
        else:
            snapshot.error_code = "internal.unhandled_exception"
            snapshot.error_category = "internal"
            snapshot.error_details = normalize_details(
                {
                    "exception_type": exception.__class__.__name__,
                    "exception_message": str(exception),
                }
            )
        failure = TaskFailure(
            metadata=snapshot.metadata,
            error_type=snapshot.error_type,
            message=snapshot.error_message,
            code=snapshot.error_code,
            category=snapshot.error_category,
            details=snapshot.error_details,
        )
        self._failures.append(failure)
        self._logger.error(
            "background_task.failed",
            task_id=snapshot.metadata.task_id,
            purpose=snapshot.metadata.purpose,
            request_id=snapshot.metadata.request_id,
            trace_id=snapshot.metadata.trace_id,
            actor_id=snapshot.metadata.actor_id,
            error_type=failure.error_type,
            error_message=failure.message,
            error_code=failure.code,
            error_category=failure.category,
            error_details=failure.details,
        )
        self._emit_snapshot(snapshot)
        self._emit_operational_event(
            OperationalEvent(
                event_type="background_task.failed",
                severity="error",
                component="tasks",
                operation=snapshot.metadata.purpose,
                correlation_id=snapshot.metadata.request_id,
                trace_id=snapshot.metadata.trace_id,
                code=snapshot.error_code,
                payload={
                    "task_id": snapshot.metadata.task_id,
                    "purpose": snapshot.metadata.purpose,
                    "code": snapshot.error_code,
                    "category": snapshot.error_category,
                    "message": snapshot.error_message,
                    "severity": "error",
                    "details": snapshot.error_details or {},
                },
            )
        )

    def _emit_snapshot(self, snapshot: TaskSnapshot) -> None:
        if self._event_sink is None:
            return
        asyncio.create_task(self._event_sink.upsert(snapshot))

    def _emit_operational_event(self, event: OperationalEvent) -> None:
        if self._observability is None:
            return
        asyncio.create_task(self._observability.emit(event))
