"""Commands for generic entity operations."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

ScalarValue = str | int | float | bool | None


class CreateEntityCommand(BaseModel):
    """Create one entity from a generic semantic payload."""

    model_config = ConfigDict(extra="forbid")

    entity_type: str = Field(min_length=1)
    values: dict[str, ScalarValue] = Field(min_length=1)
    reason: str = Field(min_length=3)


class EditEntityCommand(BaseModel):
    """Edit one entity through an opaque context ref."""

    model_config = ConfigDict(extra="forbid")

    entity_ref: str = Field(min_length=1)
    changes: dict[str, ScalarValue] = Field(min_length=1)
    expected_version: str = Field(min_length=1)
    reason: str = Field(min_length=3)


class UndoEntityMutationCommand(BaseModel):
    """Apply one previously recorded mutation undo."""

    model_config = ConfigDict(extra="forbid")

    operation_id: str = Field(min_length=1)
