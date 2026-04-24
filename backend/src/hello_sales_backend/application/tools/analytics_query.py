"""Governed analytics SQL agent tool."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from hello_sales_backend.modules.analytics_query.use_cases.analytics_query_service import (
    AnalyticsQueryService,
)
from hello_sales_backend.modules.analytics_query.use_cases.commands import (
    QueryAnalyticsDataCommand,
)
from hello_sales_backend.platform.agents.tools import (
    AgentToolDefinition,
    AgentToolExecutionContext,
)
from hello_sales_backend.shared.auth import ANALYTICS_READ_PERMISSION


class QueryAnalyticsDataToolArgs(BaseModel):
    """Strict input contract for the governed analytics SQL tool."""

    model_config = ConfigDict(extra="forbid")

    catalog_id: str = Field(min_length=1)
    sql: str = Field(min_length=1)
    reason: str = Field(min_length=3)
    max_rows: int | None = Field(default=None, ge=1, le=200)


def build_query_analytics_data_tool(
    *,
    analytics_query_service: AnalyticsQueryService,
) -> AgentToolDefinition:
    """Build the governed analytics SQL tool definition."""

    async def query_analytics_data(
        arguments: dict[str, object],
        context: AgentToolExecutionContext,
    ) -> dict[str, object]:
        result = await analytics_query_service.query_data(
            request_id=context.request_id,
            trace_id=context.trace_id,
            actor_id=context.actor_id,
            command=QueryAnalyticsDataCommand.model_validate(arguments),
        )
        return result.model_dump(mode="json")

    return AgentToolDefinition(
        name="query_analytics_data",
        description=(
            "Execute one governed read-only SQL query against the approved analytics catalog. "
            "Use only when the user is asking for analytics or tabular aggregates, include a "
            "short reason, and expect approval before execution."
        ),
        arguments_model=QueryAnalyticsDataToolArgs,
        execute=query_analytics_data,
        requires_approval=True,
        required_permissions=(ANALYTICS_READ_PERMISSION,),
    )
