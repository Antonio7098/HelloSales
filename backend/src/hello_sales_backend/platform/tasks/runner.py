"""Application-scoped background task runner."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any

from hello_sales_backend.platform.observability.events import OperationalEvent
from hello_sales_backend.platform.observability.logging import get_logger
from hello_sales_backend.platform.observability.runtime import ObservabilityRuntime
from hello_sales_backend.platform.tasks.models import (
    TaskEventSink,
    TaskMetadata,
    TaskSnapshot,
    TaskStatus,
    utc_now,
)
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
        self._task_coroutines: dict[asyncio.Task[Any], Coroutine[Any, Any, Any]] = {}
        self._snapshots: dict[str, TaskSnapshot] = {}
        self._failures: list[TaskFailure] = []
        self._event_sink = event_sink
        self._observability = observability
        self._support_tasks: set[asyncio.Task[Any]] = set()

    def start(self, metadata: TaskMetadata, coro: Coroutine[Any, Any, Any]) -> str:
        snapshot = TaskSnapshot(
            metadata=metadata,
            status=TaskStatus.RUNNING,
            created_at=utc_now(),
            started_at=utc_now(),
        )
        self._snapshots[metadata.task_id] = snapshot
        metrics = self._metrics_runtime()
        if metrics is not None:
            metrics.on_background_task_started(purpose=metadata.purpose)
        self._emit_snapshot(snapshot)
        task = asyncio.create_task(self._run_task(metadata=metadata, coro=coro))
        self._tasks[task] = metadata.task_id
        self._task_coroutines[task] = coro
        task.add_done_callback(self._handle_task_done)
        return metadata.task_id

    async def shutdown(self) -> None:
        tasks = list(self._tasks.keys())
        if tasks:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            self._tasks.clear()
        support_tasks = list(self._support_tasks)
        if support_tasks:
            await asyncio.gather(*support_tasks, return_exceptions=True)
            self._support_tasks.clear()

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
        inner_coro = self._task_coroutines.pop(task, None)
        try:
            exception = task.exception()
        except asyncio.CancelledError:
            self._close_unstarted_coro(inner_coro)
            if task_id is not None:
                snapshot = self._snapshots[task_id]
                snapshot.status = TaskStatus.CANCELLED
                snapshot.finished_at = utc_now()
                self._record_task_metrics(snapshot)
                self._emit_snapshot(snapshot)
            return
        if task_id is None:
            return
        snapshot = self._snapshots[task_id]
        snapshot.finished_at = utc_now()
        if exception is None:
            snapshot.status = TaskStatus.COMPLETED
            self._record_task_metrics(snapshot)
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
        self._record_task_metrics(snapshot)
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
        self._track_support_task(
            asyncio.create_task(self._safe_upsert_snapshot(snapshot)),
            operation="tasks.snapshot.upsert",
            metadata=snapshot.metadata,
        )

    def _emit_operational_event(self, event: OperationalEvent) -> None:
        if self._observability is None:
            return
        metadata = TaskMetadata(
            task_id=str(event.payload.get("task_id", "operational-event")),
            purpose=event.operation or event.event_type,
            request_id=event.correlation_id,
            trace_id=event.trace_id,
            actor_id=None,
        )
        self._track_support_task(
            asyncio.create_task(self._safe_emit_operational_event(event)),
            operation="tasks.operational_event.emit",
            metadata=metadata,
        )

    def _track_support_task(self, task: asyncio.Task[Any], *, operation: str, metadata: TaskMetadata) -> None:
        self._support_tasks.add(task)

        def _done(completed: asyncio.Task[Any]) -> None:
            self._support_tasks.discard(completed)
            try:
                completed.result()
            except Exception as exc:
                self._logger.error(
                    "background_support.failed",
                    operation=operation,
                    task_id=metadata.task_id,
                    purpose=metadata.purpose,
                    request_id=metadata.request_id,
                    trace_id=metadata.trace_id,
                    actor_id=metadata.actor_id,
                    error_type=exc.__class__.__name__,
                    error_message=str(exc),
                )

        task.add_done_callback(_done)

    async def _safe_upsert_snapshot(self, snapshot: TaskSnapshot) -> None:
        if self._event_sink is None:
            return
        try:
            await self._event_sink.upsert(snapshot)
        except Exception as exc:
            self._record_support_failure(
                metadata=snapshot.metadata,
                operation="tasks.snapshot.upsert",
                code="background.snapshot_emit_failed",
                exc=exc,
            )
            raise

    async def _safe_emit_operational_event(self, event: OperationalEvent) -> None:
        if self._observability is None:
            return
        try:
            await self._observability.emit(event)
        except Exception as exc:
            metadata = TaskMetadata(
                task_id=str(event.payload.get("task_id", "operational-event")),
                purpose=event.operation or event.event_type,
                request_id=event.correlation_id,
                trace_id=event.trace_id,
                actor_id=None,
            )
            self._record_support_failure(
                metadata=metadata,
                operation="tasks.operational_event.emit",
                code="background.operational_event_emit_failed",
                exc=exc,
            )
            raise

    def _record_support_failure(self, *, metadata: TaskMetadata, operation: str, code: str, exc: Exception) -> None:
        details = normalize_details(
            {
                "operation": operation,
                "exception_type": exc.__class__.__name__,
                "exception_message": str(exc),
            }
        )
        self._failures.append(
            TaskFailure(
                metadata=metadata,
                error_type=exc.__class__.__name__,
                message=str(exc),
                code=code,
                category="background",
                details=details,
            )
        )

    def _close_unstarted_coro(self, coro: Coroutine[Any, Any, Any] | None) -> None:
        if coro is None:
            return
        if getattr(coro, "cr_frame", None) is None:
            return
        if getattr(coro, "cr_await", None) is not None:
            return
        coro.close()

    def _metrics_runtime(self) -> Any | None:
        if self._observability is None:
            return None
        return getattr(self._observability, "metrics", None)

    async def _run_task(self, *, metadata: TaskMetadata, coro: Coroutine[Any, Any, Any]) -> Any:
        if self._observability is None:
            return await coro
        start_background_task_span = getattr(self._observability, "start_background_task_span", None)
        finish_background_task_span = getattr(self._observability, "finish_background_task_span", None)
        if not callable(start_background_task_span) or not callable(finish_background_task_span):
            return await coro
        with start_background_task_span(
            task_id=metadata.task_id,
            purpose=metadata.purpose,
            request_id=metadata.request_id,
            trace_id=metadata.trace_id,
        ) as span:
            try:
                result = await coro
            except asyncio.CancelledError:
                finish_background_task_span(
                    span,
                    task_id=metadata.task_id,
                    purpose=metadata.purpose,
                    status=TaskStatus.CANCELLED.value,
                    error_type="CancelledError",
                )
                raise
            except Exception as exc:
                finish_background_task_span(
                    span,
                    task_id=metadata.task_id,
                    purpose=metadata.purpose,
                    status=TaskStatus.FAILED.value,
                    error_type=exc.__class__.__name__,
                )
                raise
            finish_background_task_span(
                span,
                task_id=metadata.task_id,
                purpose=metadata.purpose,
                status=TaskStatus.COMPLETED.value,
                error_type=None,
            )
            return result

    def _record_task_metrics(self, snapshot: TaskSnapshot) -> None:
        metrics = self._metrics_runtime()
        if metrics is None:
            return
        duration_seconds: float | None = None
        if snapshot.started_at is not None and snapshot.finished_at is not None:
            duration_seconds = (snapshot.finished_at - snapshot.started_at).total_seconds()
        metrics.on_background_task_finished(
            purpose=snapshot.metadata.purpose,
            status=snapshot.status.value,
            duration_seconds=duration_seconds,
        )
