"""Worker-runs application service."""

from __future__ import annotations

from hello_sales_backend.application.workers.registry import WorkerRegistry
from hello_sales_backend.modules.worker_runs.use_cases.commands import StartWorkerRunCommand
from hello_sales_backend.modules.worker_runs.use_cases.views import (
    WorkerEventView,
    WorkerRunDetailView,
    WorkerRunSummaryView,
)
from hello_sales_backend.platform.tasks.models import TaskMetadata
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner
from hello_sales_backend.platform.workers.models import (
    WorkerExecutionMode,
    WorkerRun,
    WorkerRunStatus,
    utc_now,
)
from hello_sales_backend.platform.workers.persistence import WorkerStorePort
from hello_sales_backend.platform.workers.runtime import WorkerExecutionRuntime
from hello_sales_backend.platform.workflows.executor import WorkflowExecutor
from hello_sales_backend.shared.errors import app_error
from hello_sales_backend.shared.ids import new_id


class WorkerRunService:
    """Expose operational worker actions through a stable module facade."""

    def __init__(
        self,
        *,
        store: WorkerStorePort,
        runtime: WorkerExecutionRuntime,
        tasks: BackgroundTaskRunner,
        workflow_executor: WorkflowExecutor,
        workers: WorkerRegistry,
    ) -> None:
        self._store = store
        self._runtime = runtime
        self._tasks = tasks
        self._workflow_executor = workflow_executor
        self._workers = workers

    async def start_run(
        self,
        *,
        request_id: str | None,
        trace_id: str | None,
        actor_id: str | None,
        command: StartWorkerRunCommand,
    ) -> WorkerRunSummaryView:
        definition = self._workers.require(command.worker_name)
        validated_input = definition.input_model.model_validate(command.input_payload).model_dump(mode="json")
        execution_mode = WorkerExecutionMode(command.execution_mode)
        run = WorkerRun(
            run_id=new_id(),
            worker_name=command.worker_name,
            status=WorkerRunStatus.PENDING,
            input_payload=validated_input,
            request_id=request_id,
            trace_id=trace_id,
            actor_id=actor_id,
            execution_mode=execution_mode,
            max_attempts=command.max_attempts or definition.max_attempts,
            timeout_seconds=command.timeout_seconds or definition.timeout_seconds,
        )
        await self._store.create_run(run)
        metadata = TaskMetadata(
            task_id=new_id(),
            purpose=f"worker_run.execute.{run.worker_name}",
            request_id=request_id,
            trace_id=trace_id,
            actor_id=actor_id,
        )
        run.task_id = metadata.task_id
        run.updated_at = utc_now()
        await self._store.update_run(run)
        if execution_mode is WorkerExecutionMode.STAGEFLOW:
            self._tasks.start(
                metadata,
                self._workflow_executor.run_worker_run_workflow(
                    metadata=metadata,
                    worker_name=run.worker_name,
                    execute=lambda: self._runtime.process_run(run_id=run.run_id),
                ),
            )
        else:
            self._tasks.start(metadata, self._runtime.process_run(run_id=run.run_id))
        return self._run_summary_view(run)

    async def get_run(self, run_id: str) -> WorkerRunDetailView | None:
        run = await self._store.get_run(run_id)
        if run is None:
            return None
        return WorkerRunDetailView(
            **self._run_summary_view(run).model_dump(),
            input_payload=run.input_payload,
            output_payload=run.output_payload,
            error_details=run.error_details,
        )

    async def list_events(self, run_id: str, *, limit: int = 100) -> list[WorkerEventView]:
        await self._require_run(run_id)
        return [
            WorkerEventView(
                event_id=item.event_id,
                sequence_no=item.sequence_no,
                event_type=item.event_type,
                severity=item.severity,
                code=item.code,
                payload=item.payload,
                created_at=item.created_at.isoformat(),
            )
            for item in await self._store.list_events(run_id, limit=limit)
        ]

    async def cancel_run(self, run_id: str) -> WorkerRunSummaryView:
        run = await self._require_run(run_id)
        if run.status in {WorkerRunStatus.COMPLETED, WorkerRunStatus.FAILED, WorkerRunStatus.CANCELLED}:
            raise app_error(
                "Worker run is already terminal and cannot be cancelled",
                code="worker.run.not_cancellable",
                category="validation",
                status_code=409,
                details={"run_id": run_id, "status": run.status.value},
                operation="worker_run.cancel_run",
                component="worker",
            )
        if run.task_id is None or not self._tasks.cancel(run.task_id):
            raise app_error(
                "Worker run could not be cancelled",
                code="worker.run.cancel_failed",
                category="validation",
                status_code=409,
                details={"run_id": run_id, "task_id": run.task_id},
                operation="worker_run.cancel_run",
                component="worker",
            )
        run.updated_at = utc_now()
        await self._store.update_run(run)
        return self._run_summary_view(run)

    async def _require_run(self, run_id: str) -> WorkerRun:
        run = await self._store.get_run(run_id)
        if run is None:
            raise app_error(
                "Worker run was not found",
                code="worker.run.not_found",
                category="validation",
                status_code=404,
                details={"run_id": run_id},
                operation="worker_run.get_run",
                component="worker",
            )
        return run

    @staticmethod
    def _run_summary_view(run: WorkerRun) -> WorkerRunSummaryView:
        return WorkerRunSummaryView(
            run_id=run.run_id,
            worker_name=run.worker_name,
            status=run.status.value,
            execution_mode=run.execution_mode.value,
            request_id=run.request_id,
            trace_id=run.trace_id,
            actor_id=run.actor_id,
            task_id=run.task_id,
            attempt_count=run.attempt_count,
            max_attempts=run.max_attempts,
            timeout_seconds=run.timeout_seconds,
            provider_name=run.provider_name,
            model_name=run.model_name,
            created_at=run.created_at.isoformat(),
            updated_at=run.updated_at.isoformat(),
            started_at=run.started_at.isoformat() if run.started_at else None,
            completed_at=run.completed_at.isoformat() if run.completed_at else None,
            error_code=run.error_code,
            error_category=run.error_category,
            error_message=run.error_message,
        )
