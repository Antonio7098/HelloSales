"""Worker-runs module assembly."""

from __future__ import annotations

from dataclasses import dataclass

from hello_sales_backend.application.workers.registry import WorkerRegistry
from hello_sales_backend.modules.worker_runs.use_cases.worker_run_service import WorkerRunService
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner
from hello_sales_backend.platform.workers.persistence import WorkerStorePort
from hello_sales_backend.platform.workers.runtime import WorkerExecutionRuntime
from hello_sales_backend.platform.workflows.executor import WorkflowExecutor


@dataclass(slots=True)
class WorkerRunsModule:
    """Resolved worker-runs module bundle."""

    service: WorkerRunService


def build_worker_runs_module(
    *,
    store: WorkerStorePort,
    runtime: WorkerExecutionRuntime,
    tasks: BackgroundTaskRunner,
    workflow_executor: WorkflowExecutor,
    workers: WorkerRegistry,
) -> WorkerRunsModule:
    """Build the worker-runs module."""

    return WorkerRunsModule(
        service=WorkerRunService(
            store=store,
            runtime=runtime,
            tasks=tasks,
            workflow_executor=workflow_executor,
            workers=workers,
        )
    )
