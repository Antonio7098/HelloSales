"""Views for generic entity operations."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EntityOperationContext(BaseModel):
    """Correlation metadata for one entity operation."""

    model_config = ConfigDict(extra="forbid")

    request_id: str | None = None
    trace_id: str | None = None
    actor_id: str | None = None
    session_id: str | None = None
    run_id: str | None = None
    turn_id: str | None = None
    tool_call_id: str | None = None


class EntityMutationAuditView(EntityOperationContext):
    """Audit metadata returned to the tool caller."""


class EntityMutationResultView(BaseModel):
    """Bounded redacted result for a create/edit entity mutation."""

    model_config = ConfigDict(extra="forbid")

    operation_id: str = Field(min_length=1)
    operation: str = Field(pattern="^(create|edit)$")
    catalog_id: str = Field(min_length=1)
    catalog_version: str = Field(min_length=1)
    entity_ref: str = Field(min_length=1)
    entity_type: str = Field(min_length=1)
    display_label: str = Field(min_length=1)
    version: str = Field(min_length=1)
    changed_fields: list[str] = Field(default_factory=list)
    undo_status: str = Field(pattern="^(available|applied|conflicted|unavailable|failed)$")
    warnings: list[str] = Field(default_factory=list)
    audit: EntityMutationAuditView
