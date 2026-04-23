"""Tool bundle for the dashboard analyst agent."""

from __future__ import annotations

from hello_sales_backend.application.tools.analytics_query import (
    build_query_analytics_data_tool,
)
from hello_sales_backend.application.tools.entity_operations import (
    build_create_entity_tool,
    build_edit_entity_tool,
)
from hello_sales_backend.application.tools.web_search import build_search_web_tool
from hello_sales_backend.modules.analytics_query.use_cases.analytics_query_service import (
    AnalyticsQueryService,
)
from hello_sales_backend.modules.entity_operations import EntityOperationsService
from hello_sales_backend.modules.web_search.use_cases.web_search_service import WebSearchService
from hello_sales_backend.platform.agents.tools import AgentToolCatalog


def build_tool_catalog(
    *,
    analytics_query_service: AnalyticsQueryService,
    entity_operations_service: EntityOperationsService,
    web_search_service: WebSearchService,
    search_web_requires_approval: bool,
) -> AgentToolCatalog:
    """Build the tool catalog for the dashboard analyst agent."""

    return AgentToolCatalog(
        [
            build_query_analytics_data_tool(analytics_query_service=analytics_query_service),
            build_create_entity_tool(entity_operations_service=entity_operations_service),
            build_edit_entity_tool(entity_operations_service=entity_operations_service),
            build_search_web_tool(
                web_search_service=web_search_service,
                requires_approval=search_web_requires_approval,
            ),
        ]
    )
