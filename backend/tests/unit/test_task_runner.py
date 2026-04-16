from __future__ import annotations

import asyncio
from typing import Any

from hello_sales_backend.platform.tasks.models import TaskMetadata
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner
from hello_sales_backend.shared.errors import app_error


async def test_task_runner_records_failures() -> None:
    runner = BackgroundTaskRunner()

    async def boom() -> None:
        await asyncio.sleep(0)
        raise RuntimeError("boom")

    runner.start(TaskMetadata(task_id="task-1", purpose="test"), boom())
    await asyncio.sleep(0.01)

    failures = runner.pop_failures()
    assert len(failures) == 1
    assert failures[0].error_type == "RuntimeError"
    assert failures[0].code == "internal.unhandled_exception"
    snapshots = runner.list_snapshots()
    assert snapshots[0].status.value == "failed"
    assert runner.failure_count() == 1


async def test_task_runner_preserves_structured_app_errors() -> None:
    runner = BackgroundTaskRunner()

    async def boom() -> None:
        await asyncio.sleep(0)
        raise app_error(
            "Provider timed out",
            code="provider.timeout",
            category="provider",
            status_code=502,
            retryable=True,
            details={"provider": "fake", "timeout_seconds": 5},
            operation="provider.llm.generate",
            component="provider",
        )

    runner.start(TaskMetadata(task_id="task-2", purpose="structured-error"), boom())
    await asyncio.sleep(0.01)

    failures = runner.pop_failures()
    assert len(failures) == 1
    assert failures[0].code == "provider.timeout"
    assert failures[0].category == "provider"
    snapshots = runner.list_snapshots()
    assert snapshots[0].error_code == "provider.timeout"
    assert snapshots[0].error_category == "provider"
    assert snapshots[0].error_details is not None
    assert snapshots[0].error_details["retryable"] is True


async def test_task_runner_can_cancel_by_task_id() -> None:
    runner = BackgroundTaskRunner()

    async def slow() -> None:
        await asyncio.sleep(0.2)

    runner.start(TaskMetadata(task_id="task-3", purpose="cancel-me"), slow())
    assert runner.cancel("task-3") is True
    await asyncio.sleep(0.01)

    snapshots = runner.list_snapshots()
    assert snapshots[0].status.value == "cancelled"


async def test_task_runner_records_snapshot_sink_failures() -> None:
    class FailingSink:
        async def upsert(self, snapshot: Any) -> None:
            raise RuntimeError("sink boom")

    runner = BackgroundTaskRunner(event_sink=FailingSink())

    async def ok() -> None:
        await asyncio.sleep(0)

    runner.start(TaskMetadata(task_id="task-4", purpose="sink-failure"), ok())
    await asyncio.sleep(0.02)

    failures = runner.pop_failures()
    assert any(item.code == "background.snapshot_emit_failed" for item in failures)


async def test_task_runner_records_operational_emit_failures() -> None:
    class FailingObservability:
        async def emit(self, event: Any) -> None:
            raise RuntimeError("emit boom")

    runner = BackgroundTaskRunner(
        observability=FailingObservability(),  # type: ignore[arg-type]
    )

    async def boom() -> None:
        await asyncio.sleep(0)
        raise app_error(
            "Provider timed out",
            code="provider.timeout",
            category="provider",
            status_code=502,
            retryable=True,
            details={"provider": "fake", "timeout_seconds": 5},
            operation="provider.llm.generate",
            component="provider",
        )

    runner.start(TaskMetadata(task_id="task-5", purpose="emit-failure"), boom())
    await asyncio.sleep(0.02)

    failures = runner.pop_failures()
    assert any(item.code == "provider.timeout" for item in failures)
    assert any(item.code == "background.operational_event_emit_failed" for item in failures)
