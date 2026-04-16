"""Jobs module assembly."""

from __future__ import annotations

from dataclasses import dataclass

from hello_sales_backend.modules.jobs.use_cases.jobs_service import JobsService
from hello_sales_backend.platform.composition.providers import ProviderRegistry
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner
from hello_sales_backend.platform.workflows.executor import WorkflowExecutor


@dataclass(slots=True)
class JobsModule:
    """Resolved jobs module bundle."""

    service: JobsService


def build_jobs_module(
    *,
    providers: ProviderRegistry,
    tasks: BackgroundTaskRunner,
    workflow_executor: WorkflowExecutor,
) -> JobsModule:
    """Build the jobs module."""

    return JobsModule(
        service=JobsService(
            providers=providers,
            tasks=tasks,
            workflow_executor=workflow_executor,
        )
    )
