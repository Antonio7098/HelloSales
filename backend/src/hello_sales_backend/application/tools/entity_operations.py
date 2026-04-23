"""Generic entity mutation agent tools."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from hello_sales_backend.modules.entity_operations import EntityOperationsService
from hello_sales_backend.modules.entity_operations.use_cases.commands import (
    CreateEntityCommand,
    EditEntityCommand,
)
from hello_sales_backend.modules.entity_operations.use_cases.views import EntityOperationContext
from hello_sales_backend.platform.agents.tools import (
    AgentToolDefinition,
    AgentToolExecutionContext,
)

ScalarValue = str | int | float | bool | None


class CreateEntityToolArgs(BaseModel):
    """Strict input contract for generic entity creation."""

    model_config = ConfigDict(extra="forbid")

    entity_type: str = Field(min_length=1)
    values: dict[str, ScalarValue] = Field(min_length=1)
    reason: str = Field(min_length=3)


class EditEntityToolArgs(BaseModel):
    """Strict input contract for generic entity edits."""

    model_config = ConfigDict(extra="forbid")

    entity_ref: str = Field(min_length=1)
    changes: dict[str, ScalarValue] = Field(min_length=1)
    expected_version: str = Field(min_length=1)
    reason: str = Field(min_length=3)


def _entity_context(context: AgentToolExecutionContext) -> EntityOperationContext:
    return EntityOperationContext(
        request_id=context.request_id,
        trace_id=context.trace_id,
        actor_id=context.actor_id,
        session_id=context.session_id,
        run_id=context.run_id,
        turn_id=context.turn_id,
        tool_call_id=context.tool_call_id,
    )


def build_create_entity_tool(*, entity_operations_service: EntityOperationsService) -> AgentToolDefinition:
    """Build the generic create-entity tool definition."""

    async def create_entity(
        arguments: dict[str, object],
        context: AgentToolExecutionContext,
    ) -> dict[str, object]:
        result = await entity_operations_service.create_entity(
            context=_entity_context(context),
            command=CreateEntityCommand.model_validate(arguments),
        )
        return result.model_dump(mode="json")

    return AgentToolDefinition(
        name="create_entity",
        description=(
            "Create one semantic entity using the canonical schema already supplied in context. "
            "Use only for approved company_profile or product mutations, include a short reason, "
            "and expect approval before execution."
        ),
        arguments_model=CreateEntityToolArgs,
        execute=create_entity,
        requires_approval=True,
    )


def build_edit_entity_tool(*, entity_operations_service: EntityOperationsService) -> AgentToolDefinition:
    """Build the generic edit-entity tool definition."""

    async def edit_entity(
        arguments: dict[str, object],
        context: AgentToolExecutionContext,
    ) -> dict[str, object]:
        result = await entity_operations_service.edit_entity(
            context=_entity_context(context),
            command=EditEntityCommand.model_validate(arguments),
        )
        return result.model_dump(mode="json")

    return AgentToolDefinition(
        name="edit_entity",
        description=(
            "Edit one semantic entity through an opaque context ref and expected version. "
            "Use only when you already have the entity_ref from prior tool context, include a short reason, "
            "and expect approval before execution."
        ),
        arguments_model=EditEntityToolArgs,
        execute=edit_entity,
        requires_approval=True,
    )
