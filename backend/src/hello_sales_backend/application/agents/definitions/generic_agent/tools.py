"""Tool bundle for the dashboard analyst agent."""

from __future__ import annotations

from hello_sales_backend.application.tools.analytics_query import (
    build_query_analytics_data_tool,
)
from hello_sales_backend.modules.analytics_query.use_cases.analytics_query_service import (
    AnalyticsQueryService,
)
from hello_sales_backend.platform.agents.tools import AgentToolCatalog


def build_tool_catalog(
    *,
    analytics_query_service: AnalyticsQueryService,
) -> AgentToolCatalog:
    """Build the tool catalog for the dashboard analyst agent."""

    return AgentToolCatalog(
        [
            build_query_analytics_data_tool(analytics_query_service=analytics_query_service),
        ]
    )
