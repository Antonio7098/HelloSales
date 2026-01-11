"""Product entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID


@dataclass
class Product:
    """A product or service being sold."""

    id: UUID
    org_id: UUID
    name: str

    description: str | None = None
    category: str | None = None

    # Product details for AI context
    key_features: list[str] = field(default_factory=list)
    pricing_info: dict[str, Any] = field(default_factory=dict)
    target_audience: str | None = None
    competitive_advantages: str | None = None
    use_cases: list[str] = field(default_factory=list)

    is_active: bool = True

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Product name is required")

    def to_context_dict(self) -> dict[str, Any]:
        """Convert to dict for LLM context injection."""
        ctx: dict[str, Any] = {
            "name": self.name,
        }
        if self.description:
            ctx["description"] = self.description
        if self.category:
            ctx["category"] = self.category
        if self.key_features:
            ctx["key_features"] = self.key_features
        if self.target_audience:
            ctx["target_audience"] = self.target_audience
        if self.competitive_advantages:
            ctx["competitive_advantages"] = self.competitive_advantages
        if self.use_cases:
            ctx["use_cases"] = self.use_cases
        return ctx
