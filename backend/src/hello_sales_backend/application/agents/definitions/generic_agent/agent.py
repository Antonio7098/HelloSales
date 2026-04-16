"""Concrete baseline generic agent definition."""

from __future__ import annotations

from hello_sales_backend.application.agents.contracts import AgentDefinition
from hello_sales_backend.modules.jobs.use_cases.jobs_service import JobsService
from hello_sales_backend.modules.system.use_cases.system_service import SystemService

from .policy import KeywordToolSelectionPolicy
from .prompts import build_fallback_response, build_messages
from .tools import build_tool_catalog


def build_generic_agent_definition(
    *,
    system_service: SystemService,
    jobs_service: JobsService,
) -> AgentDefinition:
    """Build the baseline generic agent definition."""

    return AgentDefinition(
        agent_id="generic",
        display_name="Generic Agent",
        tools=build_tool_catalog(system_service=system_service, jobs_service=jobs_service),
        selection_policy=KeywordToolSelectionPolicy(),
        build_messages=build_messages,
        build_fallback_response=build_fallback_response,
    )
