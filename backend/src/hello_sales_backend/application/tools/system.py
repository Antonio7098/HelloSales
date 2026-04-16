"""System-facing reusable agent tools."""

from __future__ import annotations

from hello_sales_backend.modules.system.use_cases.system_service import SystemService
from hello_sales_backend.platform.agents.tools import (
    AgentToolDefinition,
    AgentToolExecutionContext,
)


def build_get_runtime_status_tool(*, system_service: SystemService) -> AgentToolDefinition:
    """Build the runtime status tool definition."""

    async def get_runtime_status(
        _arguments: dict[str, object],
        _context: AgentToolExecutionContext,
    ) -> dict[str, object]:
        return (await system_service.get_status()).model_dump(mode="json")

    return AgentToolDefinition(
        name="get_runtime_status",
        description="Return top-level runtime status information.",
        execute=get_runtime_status,
    )
