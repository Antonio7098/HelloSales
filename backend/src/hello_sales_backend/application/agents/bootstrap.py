"""Application agent registry assembly."""

from __future__ import annotations

from hello_sales_backend.modules.analytics_query.use_cases.analytics_query_service import (
    AnalyticsQueryService,
)
from hello_sales_backend.modules.entity_operations import EntityOperationsService
from hello_sales_backend.modules.jobs.use_cases.jobs_service import JobsService
from hello_sales_backend.modules.semantic_catalog import SemanticCatalogService
from hello_sales_backend.modules.system.use_cases.system_service import SystemService
from hello_sales_backend.modules.web_search.use_cases.web_search_service import WebSearchService
from hello_sales_backend.platform.config.settings import Settings

from .definitions.generic_agent.agent import build_generic_agent_definition
from .definitions.observer_agent.agent import build_observer_agent_definition
from .registry import AgentRegistry


def build_agent_registry(
    *,
    settings: Settings,
    system_service: SystemService,
    jobs_service: JobsService,
    analytics_query_service: AnalyticsQueryService,
    semantic_catalog_service: SemanticCatalogService,
    entity_operations_service: EntityOperationsService,
    web_search_service: WebSearchService,
) -> AgentRegistry:
    """Build the application agent registry."""

    return AgentRegistry(
        [
            build_generic_agent_definition(
                analytics_query_service=analytics_query_service,
                semantic_catalog_service=semantic_catalog_service,
                entity_operations_service=entity_operations_service,
                web_search_service=web_search_service,
                search_web_requires_approval=settings.web_search_requires_approval,
            ),
            build_observer_agent_definition(system_service=system_service, jobs_service=jobs_service),
        ],
        default_agent_id="generic",
    )
