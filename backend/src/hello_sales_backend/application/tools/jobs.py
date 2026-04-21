"""Jobs-facing reusable agent tools."""

from __future__ import annotations

from pydantic import BaseModel

from hello_sales_backend.modules.jobs.use_cases.commands import StartDiagnosticJobCommand
from hello_sales_backend.modules.jobs.use_cases.jobs_service import JobsService
from hello_sales_backend.platform.agents.tools import (
    AgentToolDefinition,
    AgentToolExecutionContext,
)
from hello_sales_backend.shared.errors import app_error


class ListRecentTasksToolArgs(BaseModel):
    limit: int = 10


class GetTaskToolArgs(BaseModel):
    task_id: str


class RunDiagnosticJobToolArgs(BaseModel):
    prompt: str = "Run a diagnostic check."


def build_list_recent_tasks_tool(*, jobs_service: JobsService) -> AgentToolDefinition:
    """Build the recent-tasks tool definition."""

    def list_recent_tasks(
        arguments: dict[str, object],
        _context: AgentToolExecutionContext,
    ) -> dict[str, object]:
        limit_value = arguments.get("limit", 10)
        limit = int(limit_value) if isinstance(limit_value, (int, str)) else 10
        items = jobs_service.list_tasks().items[:limit]
        return {"items": [item.model_dump(mode="json") for item in items], "limit": limit}

    return AgentToolDefinition(
        name="list_recent_tasks",
        description="List recent operational background tasks.",
        arguments_model=ListRecentTasksToolArgs,
        execute=list_recent_tasks,
    )


def build_get_task_tool(*, jobs_service: JobsService) -> AgentToolDefinition:
    """Build the get-task tool definition."""

    def get_task(
        arguments: dict[str, object],
        _context: AgentToolExecutionContext,
    ) -> dict[str, object]:
        task_id = str(arguments.get("task_id", "")).strip()
        if not task_id:
            raise app_error(
                "Task identifier is required",
                code="agent.tool.get_task.invalid_arguments",
                category="validation",
                status_code=400,
                details={"arguments": arguments},
                operation="agent.tool.get_task",
                component="agent",
            )
        task = jobs_service.get_task(task_id)
        return {"task_id": task_id, "task": task.model_dump(mode="json") if task is not None else None}

    return AgentToolDefinition(
        name="get_task",
        description="Fetch one operational background task by id.",
        arguments_model=GetTaskToolArgs,
        execute=get_task,
    )


def build_run_diagnostic_job_tool(*, jobs_service: JobsService) -> AgentToolDefinition:
    """Build the diagnostic-job tool definition."""

    def run_diagnostic_job(
        arguments: dict[str, object],
        context: AgentToolExecutionContext,
    ) -> dict[str, object]:
        prompt = str(arguments.get("prompt", "")).strip() or "Run a diagnostic check."
        result = jobs_service.start_diagnostic_job(
            request_id=context.request_id,
            trace_id=context.trace_id,
            actor_id=context.actor_id,
            command=StartDiagnosticJobCommand(prompt=prompt),
        )
        return result.model_dump(mode="json")

    return AgentToolDefinition(
        name="run_diagnostic_job",
        description="Start the diagnostic workflow job.",
        arguments_model=RunDiagnosticJobToolArgs,
        execute=run_diagnostic_job,
        requires_approval=True,
    )
