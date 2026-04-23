"""Reusable runtime contracts for agent tool execution."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from copy import deepcopy
from dataclasses import dataclass
from inspect import isawaitable
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from hello_sales_backend.platform.llm import ProviderToolDefinition
from hello_sales_backend.shared.errors import AppError, app_error


class EmptyToolArguments(BaseModel):
    """Strict empty argument model for tools that take no input."""

    model_config = ConfigDict(extra="forbid")


@dataclass(slots=True, frozen=True)
class AgentToolExecutionContext:
    """Correlation metadata passed into tool execution."""

    request_id: str | None
    trace_id: str | None
    actor_id: str | None
    session_id: str | None = None
    run_id: str | None = None
    turn_id: str | None = None
    tool_call_id: str | None = None


@dataclass(slots=True, frozen=True)
class AgentToolRequest:
    """Selected tool invocation request."""

    name: str
    arguments: dict[str, object]


ToolCallback = Callable[[dict[str, object], AgentToolExecutionContext], Awaitable[dict[str, object]] | dict[str, object]]


def _normalize_schema_node(node: Any) -> None:
    if isinstance(node, dict):
        node_type = node.get("type")
        if node_type == "object":
            node.setdefault("additionalProperties", False)
            properties = node.get("properties")
            if isinstance(properties, dict):
                for value in properties.values():
                    _normalize_schema_node(value)
        elif node_type == "array":
            _normalize_schema_node(node.get("items"))
        for key in ("$defs", "definitions", "dependentSchemas", "properties"):
            child = node.get(key)
            if isinstance(child, dict):
                for value in child.values():
                    _normalize_schema_node(value)
        for key in ("allOf", "anyOf", "oneOf", "prefixItems"):
            child = node.get(key)
            if isinstance(child, list):
                for value in child:
                    _normalize_schema_node(value)
        for key in ("not", "if", "then", "else", "contains", "items"):
            _normalize_schema_node(node.get(key))
    elif isinstance(node, list):
        for value in node:
            _normalize_schema_node(value)


def _strict_tool_schema(model_type: type[BaseModel]) -> dict[str, object]:
    schema = deepcopy(model_type.model_json_schema())
    _normalize_schema_node(schema)
    return schema


@dataclass(slots=True)
class AgentToolDefinition:
    """Registered tool metadata, argument contract, and executor."""

    name: str
    description: str
    arguments_model: type[BaseModel]
    execute: ToolCallback
    requires_approval: bool = False

    def provider_definition(self) -> ProviderToolDefinition:
        return ProviderToolDefinition(
            name=self.name,
            description=self.description,
            parameters=_strict_tool_schema(self.arguments_model),
        )

    def validate_arguments(self, arguments: dict[str, object]) -> dict[str, object]:
        try:
            validated = self.arguments_model.model_validate(arguments)
        except ValidationError as exc:
            raise app_error(
                "Agent tool arguments did not satisfy the declared schema",
                code="agent.tool.invalid_arguments",
                category="validation",
                status_code=400,
                details={"tool_name": self.name, "arguments": arguments, "errors": exc.errors()},
                operation="agent.tool.validate_arguments",
                component="agent",
                exc=exc,
            ) from exc
        return validated.model_dump(mode="json")

    def validate_provider_arguments(
        self,
        *,
        arguments: dict[str, object],
        tool_call_id: str,
        run_id: str,
        turn_id: str,
    ) -> dict[str, object]:
        try:
            return self.validate_arguments(arguments)
        except AppError as exc:
            if exc.code != "agent.tool.invalid_arguments":
                raise
            raise app_error(
                "Provider returned arguments that do not satisfy the declared tool schema",
                code="provider.invalid_tool_arguments",
                category="provider",
                status_code=502,
                details={
                    "run_id": run_id,
                    "turn_id": turn_id,
                    "tool_call_id": tool_call_id,
                    "tool_name": self.name,
                    "arguments": arguments,
                    "errors": exc.details.get("errors"),
                },
                operation="agent.tool.validate_provider_arguments",
                component="agent",
                exc=exc,
            ) from exc


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

    def provider_definitions(self) -> list[ProviderToolDefinition]:
        return [definition.provider_definition() for definition in self._definitions.values()]

    async def execute(
        self,
        *,
        name: str,
        arguments: dict[str, object],
        context: AgentToolExecutionContext,
    ) -> dict[str, object]:
        definition = self.require(name)
        validated_arguments = definition.validate_arguments(arguments)
        result = definition.execute(validated_arguments, context)
        if isawaitable(result):
            resolved = await result
        else:
            resolved = result
        return dict(resolved)
