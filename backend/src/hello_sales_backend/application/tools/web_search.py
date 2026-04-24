"""Public web-search agent tool."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from hello_sales_backend.modules.web_search.use_cases.commands import SearchWebCommand
from hello_sales_backend.modules.web_search.use_cases.web_search_service import WebSearchService
from hello_sales_backend.platform.agents.tools import (
    AgentToolDefinition,
    AgentToolExecutionContext,
)
from hello_sales_backend.shared.auth import WEB_SEARCH_USE_PERMISSION
from hello_sales_backend.shared.errors import AppError

SEARCH_WEB_MAX_ATTEMPTS = 3


class SearchWebToolArgs(BaseModel):
    """Strict input contract for the public web-search tool."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=3, max_length=500)
    max_results: int | None = Field(default=None, ge=1, le=20)
    search_depth: str = Field(default="basic", pattern="^(basic|advanced)$")
    topic: str = Field(default="general", pattern="^(general|news)$")
    time_range: str | None = Field(default=None, pattern="^(day|week|month|year|d|w|m|y)$")
    include_domains: list[str] = Field(default_factory=list, max_length=10)
    exclude_domains: list[str] = Field(default_factory=list, max_length=10)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    include_raw_content: bool = False


def build_search_web_tool(
    *,
    web_search_service: WebSearchService,
    requires_approval: bool,
) -> AgentToolDefinition:
    """Build the public web-search tool definition."""

    async def search_web(
        arguments: dict[str, object],
        context: AgentToolExecutionContext,
    ) -> dict[str, object]:
        command = SearchWebCommand.model_validate(arguments)
        last_error: AppError | None = None
        for attempt in range(1, SEARCH_WEB_MAX_ATTEMPTS + 1):
            try:
                result = await web_search_service.search(
                    request_id=context.request_id,
                    trace_id=context.trace_id,
                    actor_id=context.actor_id,
                    command=command,
                )
                return result.model_dump(mode="json")
            except AppError as exc:
                last_error = exc
                if not exc.retryable or attempt >= SEARCH_WEB_MAX_ATTEMPTS:
                    raise
        raise last_error or RuntimeError("search_web retry loop exited unexpectedly")

    return AgentToolDefinition(
        name="search_web",
        description=(
            "Search the public web for current or external information. Do not use for secrets, "
            "private customer data, or internal-only analytics; use governed SQL for approved "
            "internal analytics questions. Return and cite source URLs from the tool result."
        ),
        arguments_model=SearchWebToolArgs,
        execute=search_web,
        requires_approval=requires_approval,
        required_permissions=(WEB_SEARCH_USE_PERMISSION,),
    )
