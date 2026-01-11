"""Sales script entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID


ScriptType = Literal["cold_call", "follow_up", "demo", "closing", "general"]


@dataclass
class SalesScript:
    """A generated or managed sales script."""

    id: UUID
    org_id: UUID
    name: str
    content: str

    # Associations (can be any combination)
    product_id: UUID | None = None
    client_id: UUID | None = None

    description: str | None = None
    script_type: ScriptType = "general"

    # Script components
    key_talking_points: list[str] = field(default_factory=list)
    objection_handlers: dict[str, str] = field(default_factory=dict)  # objection -> response
    discovery_questions: list[str] = field(default_factory=list)
    closing_techniques: list[str] = field(default_factory=list)

    # Generation metadata
    generated_by_session_id: UUID | None = None
    generation_prompt: str | None = None
    model_id: str | None = None

    # Versioning
    version: int = 1
    parent_script_id: UUID | None = None

    is_active: bool = True

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Script name is required")
        if not self.content:
            raise ValueError("Script content is required")

    def to_context_dict(self) -> dict[str, Any]:
        """Convert to dict for reference in LLM calls."""
        return {
            "name": self.name,
            "type": self.script_type,
            "content": self.content,
            "key_talking_points": self.key_talking_points,
            "objection_handlers": self.objection_handlers,
            "discovery_questions": self.discovery_questions,
            "closing_techniques": self.closing_techniques,
        }
