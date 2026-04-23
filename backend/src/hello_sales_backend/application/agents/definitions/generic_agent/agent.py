"""Concrete dashboard analyst agent definition."""

from __future__ import annotations

from hello_sales_backend.application.agents.contracts import AgentDefinition
from hello_sales_backend.modules.analytics_query.use_cases.analytics_query_service import (
    AnalyticsQueryService,
)
from hello_sales_backend.modules.analytics_query.use_cases.ports import AnalyticsCatalog
from hello_sales_backend.modules.web_search.use_cases.web_search_service import WebSearchService

from .prompts import build_generic_agent_prompt
from .tools import build_tool_catalog


def _build_schema_text(catalog: AnalyticsCatalog) -> str:
    relation_lines: list[str] = []
    for relation in sorted(catalog.relations.values(), key=lambda item: item.name):
        column_names = ", ".join(list(relation.columns)[:8])
        relation_lines.append(
            f"- {relation.name}: {relation.description}. Key columns: {column_names}."
        )
    joined_relations = " ".join(relation_lines)
    return (
        "Approved analytics schema context: "
        f"catalog_id={catalog.catalog_id}; dialect={catalog.dialect}. "
        f"{catalog.description} "
        "Approved relations: "
        f"{joined_relations} "
        "There is no generic `companies` table unless it appears in the approved relations above."
    )


def _fallback_schema_text() -> str:
    return (
        "Approved analytics schema context: catalog_id=scaffold_stage; dialect=postgres. "
        "Approved relations include company_profiles, products, analytics_daily_pipeline, and analytics_rep_performance. "
        "Use the closest matching approved relation rather than asking the user to name the schema."
    )


def build_generic_agent_definition(
    *,
    analytics_query_service: AnalyticsQueryService,
    web_search_service: WebSearchService,
    search_web_requires_approval: bool,
) -> AgentDefinition:
    """Build the company analyst agent definition."""

    catalog_store = getattr(analytics_query_service, "_catalogs", None)
    schema_text = _fallback_schema_text()
    if catalog_store is not None:
        catalog = catalog_store.get_catalog("scaffold_stage")
        schema_text = _build_schema_text(catalog)
    return AgentDefinition(
        agent_id="generic",
        display_name="Company Analyst",
        tools=build_tool_catalog(
            analytics_query_service=analytics_query_service,
            web_search_service=web_search_service,
            search_web_requires_approval=search_web_requires_approval,
        ),
        prompt=build_generic_agent_prompt(schema_text=schema_text),
    )
