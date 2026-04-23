"""Application agent registry assembly."""

from __future__ import annotations

from hello_sales_backend.modules.analytics_query.use_cases.analytics_query_service import (
    AnalyticsQueryService,
)
from hello_sales_backend.modules.jobs.use_cases.jobs_service import JobsService
from hello_sales_backend.modules.system.use_cases.system_service import SystemService

from .definitions.generic_agent.agent import build_generic_agent_definition
from .definitions.observer_agent.agent import build_observer_agent_definition
from .registry import AgentRegistry


def build_agent_registry(
    *,
    system_service: SystemService,
    jobs_service: JobsService,
    analytics_query_service: AnalyticsQueryService,
) -> AgentRegistry:
    """Build the application agent registry."""

    return AgentRegistry(
        [
            build_generic_agent_definition(
                analytics_query_service=analytics_query_service,
            ),
            build_observer_agent_definition(system_service=system_service, jobs_service=jobs_service),
        ],
        default_agent_id="generic",
    )
