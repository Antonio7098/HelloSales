"""Client entity - prospective or current customers."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID


@dataclass
class Client:
    """A prospective or current customer."""

    id: UUID
    org_id: UUID
    name: str

    company: str | None = None
    title: str | None = None
    industry: str | None = None
    email: str | None = None

    # Client profile for AI context
    pain_points: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    objection_patterns: list[str] = field(default_factory=list)
    communication_style: str | None = None
    decision_criteria: list[str] = field(default_factory=list)

    is_active: bool = True

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Client name is required")

    def to_context_dict(self) -> dict[str, Any]:
        """Convert to dict for LLM context injection."""
        ctx: dict[str, Any] = {
            "name": self.name,
        }
        if self.company:
            ctx["company"] = self.company
        if self.title:
            ctx["title"] = self.title
        if self.industry:
            ctx["industry"] = self.industry
        if self.pain_points:
            ctx["pain_points"] = self.pain_points
        if self.goals:
            ctx["goals"] = self.goals
        if self.objection_patterns:
            ctx["objection_patterns"] = self.objection_patterns
        if self.communication_style:
            ctx["communication_style"] = self.communication_style
        if self.decision_criteria:
            ctx["decision_criteria"] = self.decision_criteria
        return ctx
