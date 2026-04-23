"""Concrete dashboard analyst agent definition."""

from __future__ import annotations

from hello_sales_backend.application.agents.contracts import AgentDefinition
from hello_sales_backend.modules.analytics_query.use_cases.analytics_query_service import (
    AnalyticsQueryService,
)
from hello_sales_backend.modules.entity_operations import EntityOperationsService
from hello_sales_backend.modules.semantic_catalog import SemanticCatalogService
from hello_sales_backend.modules.semantic_catalog.use_cases.views import (
    SemanticCatalogView,
)
from hello_sales_backend.modules.web_search.use_cases.web_search_service import WebSearchService

from .prompts import build_generic_agent_prompt
from .tools import build_tool_catalog


def _build_schema_text(catalog: SemanticCatalogView) -> str:
    relation_lines: list[str] = []
    writable_lines: list[str] = []
    for entity in sorted(catalog.entities.values(), key=lambda item: item.entity_type):
        if entity.analytics is not None and entity.analytics.enabled:
            column_names = ", ".join(
                field.name for field in list(entity.fields.values())[:8] if field.analytics.enabled
            )
            relation_name = entity.analytics.relation_name or entity.storage.relation_name
            relation_lines.append(
                f"- {relation_name}: {entity.analytics.description or entity.description}. Key columns: {column_names}."
            )
        if entity.mutations is not None and (entity.mutations.create_allowed or entity.mutations.edit_allowed):
            create_fields = ", ".join(
                field.name
                for field in entity.fields.values()
                if field.mutations.write_policy in {"editable", "create_only"}
            )
            edit_fields = ", ".join(
                field.name
                for field in entity.fields.values()
                if field.mutations.write_policy == "editable"
            )
            writable_lines.append(
                f"- {entity.entity_type}: create fields [{create_fields or 'none'}]; "
                f"edit fields [{edit_fields or 'none'}]; edit requires entity_ref and expected_version."
            )
    joined_relations = " ".join(relation_lines)
    joined_writable = " ".join(writable_lines)
    return (
        "Approved analytics schema context: "
        f"catalog_id={catalog.catalog_id}; dialect={catalog.dialect}. "
        f"{catalog.description} "
        "Approved relations: "
        f"{joined_relations} "
        "Writable semantic entity context: "
        f"{joined_writable} "
        "There is no generic `companies` table unless it appears in the approved relations above."
    )


def _fallback_schema_text() -> str:
    return (
        "Approved analytics schema context: catalog_id=scaffold_stage; dialect=postgres. "
        "Approved relations include company_profiles, products, analytics_daily_pipeline, and analytics_rep_performance. "
        "Writable semantic entities include company_profile and product. "
        "Use the closest matching approved relation rather than asking the user to name the schema."
    )


def build_generic_agent_definition(
    *,
    analytics_query_service: AnalyticsQueryService,
    semantic_catalog_service: SemanticCatalogService,
    entity_operations_service: EntityOperationsService,
    web_search_service: WebSearchService,
    search_web_requires_approval: bool,
) -> AgentDefinition:
    """Build the company analyst agent definition."""

    schema_text = _fallback_schema_text()
    try:
        schema_text = _build_schema_text(
            semantic_catalog_service.get_catalog(entity_operations_service.describe_catalog().catalog_id)
        )
    except Exception:
        schema_text = _fallback_schema_text()
    return AgentDefinition(
        agent_id="generic",
        display_name="Company Analyst",
        tools=build_tool_catalog(
            analytics_query_service=analytics_query_service,
            entity_operations_service=entity_operations_service,
            web_search_service=web_search_service,
            search_web_requires_approval=search_web_requires_approval,
        ),
        prompt=build_generic_agent_prompt(schema_text=schema_text),
    )
