"""Concrete observer agent definition."""

from __future__ import annotations

from hello_sales_backend.application.agents.contracts import AgentDefinition
from hello_sales_backend.modules.jobs.use_cases.jobs_service import JobsService
from hello_sales_backend.modules.system.use_cases.system_service import SystemService

from .prompts import OBSERVER_AGENT_RESPONSE_PROMPT
from .tools import build_tool_catalog


def build_observer_agent_definition(
    *,
    system_service: SystemService,
    jobs_service: JobsService,
) -> AgentDefinition:
    """Build the observer agent definition."""

    return AgentDefinition(
        agent_id="observer",
        display_name="Observer Agent",
        tools=build_tool_catalog(system_service=system_service, jobs_service=jobs_service),
        prompt=OBSERVER_AGENT_RESPONSE_PROMPT,
    )
