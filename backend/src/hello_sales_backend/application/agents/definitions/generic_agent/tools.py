"""Tool bundle for the baseline generic agent."""

from __future__ import annotations

from hello_sales_backend.application.tools.jobs import (
    build_get_task_tool,
    build_list_recent_tasks_tool,
    build_run_diagnostic_job_tool,
)
from hello_sales_backend.application.tools.system import build_get_runtime_status_tool
from hello_sales_backend.modules.jobs.use_cases.jobs_service import JobsService
from hello_sales_backend.modules.system.use_cases.system_service import SystemService
from hello_sales_backend.platform.agents.tools import AgentToolCatalog


def build_tool_catalog(
    *,
    system_service: SystemService,
    jobs_service: JobsService,
) -> AgentToolCatalog:
    """Build the concrete tool catalog for the baseline generic agent."""

    return AgentToolCatalog(
        [
            build_get_runtime_status_tool(system_service=system_service),
            build_list_recent_tasks_tool(jobs_service=jobs_service),
            build_get_task_tool(jobs_service=jobs_service),
            build_run_diagnostic_job_tool(jobs_service=jobs_service),
        ]
    )
