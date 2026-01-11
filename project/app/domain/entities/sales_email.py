"""Sales email entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID


EmailType = Literal["cold_outreach", "follow_up", "proposal", "closing", "general"]


@dataclass
class SalesEmail:
    """A generated or managed sales email template."""

    id: UUID
    org_id: UUID
    name: str
    subject: str
    body: str

    # Associations (can be any combination)
    product_id: UUID | None = None
    client_id: UUID | None = None

    description: str | None = None
    email_type: EmailType = "general"

    call_to_action: str | None = None

    # Personalization hints - fields that should be customized per-send
    personalization_fields: list[str] = field(default_factory=list)

    # Generation metadata
    generated_by_session_id: UUID | None = None
    generation_prompt: str | None = None
    model_id: str | None = None

    # Versioning
    version: int = 1
    parent_email_id: UUID | None = None

    is_active: bool = True

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Email name is required")
        if not self.subject:
            raise ValueError("Email subject is required")
        if not self.body:
            raise ValueError("Email body is required")

    def to_context_dict(self) -> dict[str, Any]:
        """Convert to dict for reference in LLM calls."""
        return {
            "name": self.name,
            "type": self.email_type,
            "subject": self.subject,
            "body": self.body,
            "call_to_action": self.call_to_action,
            "personalization_fields": self.personalization_fields,
        }
