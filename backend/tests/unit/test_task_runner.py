from __future__ import annotations

import asyncio

from hello_sales_backend.platform.tasks.models import TaskMetadata
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner
from hello_sales_backend.shared.errors import app_error


async def test_task_runner_records_failures():
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


async def test_task_runner_preserves_structured_app_errors():
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


async def test_task_runner_can_cancel_by_task_id():
    runner = BackgroundTaskRunner()

    async def slow() -> None:
        await asyncio.sleep(0.2)

    runner.start(TaskMetadata(task_id="task-3", purpose="cancel-me"), slow())
    assert runner.cancel("task-3") is True
    await asyncio.sleep(0.01)

    snapshots = runner.list_snapshots()
    assert snapshots[0].status.value == "cancelled"
