"""Reusable runtime contracts for agent tool execution."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from inspect import isawaitable

from hello_sales_backend.shared.errors import app_error


@dataclass(slots=True, frozen=True)
class AgentToolExecutionContext:
    """Correlation metadata passed into tool execution."""

    request_id: str | None
    trace_id: str | None
    actor_id: str | None


@dataclass(slots=True, frozen=True)
class AgentToolRequest:
    """Selected tool invocation request."""

    name: str
    arguments: dict[str, object]


ToolCallback = Callable[[dict[str, object], AgentToolExecutionContext], Awaitable[dict[str, object]] | dict[str, object]]


@dataclass(slots=True)
class AgentToolDefinition:
    """Registered tool metadata and executor."""

    name: str
    description: str
    execute: ToolCallback
    requires_approval: bool = False


class AgentToolCatalog:
    """Resolved set of tools exposed to the generic agent."""

    def __init__(self, definitions: list[AgentToolDefinition]) -> None:
        self._definitions = {item.name: item for item in definitions}

    def has(self, name: str) -> bool:
        return name in self._definitions

    def require(self, name: str) -> AgentToolDefinition:
        definition = self._definitions.get(name)
        if definition is None:
            raise app_error(
                "Requested agent tool is not registered",
                code="agent.tool.not_found",
                category="validation",
                status_code=404,
                details={"tool_name": name},
                operation="agent.tool.require",
                component="agent",
            )
        return definition

    async def execute(
        self,
        *,
        name: str,
        arguments: dict[str, object],
        context: AgentToolExecutionContext,
    ) -> dict[str, object]:
        result = self.require(name).execute(arguments, context)
        if isawaitable(result):
            resolved = await result
        else:
            resolved = result
        return dict(resolved)
