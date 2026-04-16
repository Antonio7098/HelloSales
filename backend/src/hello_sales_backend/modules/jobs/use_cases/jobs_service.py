"""Jobs application service."""

from __future__ import annotations

from typing import Any

from hello_sales_backend.modules.jobs.use_cases.commands import StartDiagnosticJobCommand
from hello_sales_backend.modules.jobs.use_cases.views import (
    JobTaskListView,
    JobTaskView,
    StartDiagnosticJobView,
)
from hello_sales_backend.modules.jobs.workflows.diagnostic_workflow import run_diagnostic_workflow
from hello_sales_backend.platform.composition.providers import ProviderRegistry
from hello_sales_backend.platform.tasks.models import TaskMetadata
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner
from hello_sales_backend.platform.workflows.executor import WorkflowExecutor
from hello_sales_backend.shared.ids import new_id


class JobsService:
    """Own lightweight operational jobs and diagnostics."""

    def __init__(
        self,
        *,
        providers: ProviderRegistry,
        tasks: BackgroundTaskRunner,
        workflow_executor: WorkflowExecutor,
    ) -> None:
        self._providers = providers
        self._tasks = tasks
        self._workflow_executor = workflow_executor

    def list_tasks(self) -> JobTaskListView:
        return JobTaskListView(items=[self._snapshot_to_view(item) for item in self._tasks.list_snapshots()])

    def get_task(self, task_id: str) -> JobTaskView | None:
        for snapshot in self._tasks.list_snapshots():
            if snapshot.metadata.task_id == task_id:
                return self._snapshot_to_view(snapshot)
        return None

    def start_diagnostic_job(
        self,
        *,
        request_id: str | None,
        trace_id: str | None,
        actor_id: str | None,
        command: StartDiagnosticJobCommand,
    ) -> StartDiagnosticJobView:
        metadata = TaskMetadata(
            task_id=new_id(),
            purpose="diagnostic_llm_workflow",
            request_id=request_id,
            trace_id=trace_id,
            actor_id=actor_id,
        )
        self._tasks.start(
            metadata,
            run_diagnostic_workflow(
                metadata=metadata,
                workflow_executor=self._workflow_executor,
                llm_provider=self._providers.llm,
                prompt=command.prompt,
            ),
        )
        return StartDiagnosticJobView(task_id=metadata.task_id, purpose=metadata.purpose, status="running")

    @staticmethod
    def _snapshot_to_view(snapshot: Any) -> JobTaskView:
        return JobTaskView(
            task_id=snapshot.metadata.task_id,
            purpose=snapshot.metadata.purpose,
            status=snapshot.status.value,
            request_id=snapshot.metadata.request_id,
            trace_id=snapshot.metadata.trace_id,
            actor_id=snapshot.metadata.actor_id,
            error_type=snapshot.error_type,
            error_message=snapshot.error_message,
            created_at=snapshot.created_at.isoformat(),
            started_at=snapshot.started_at.isoformat() if snapshot.started_at else None,
            finished_at=snapshot.finished_at.isoformat() if snapshot.finished_at else None,
        )
