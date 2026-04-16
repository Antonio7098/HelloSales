"""Operational event models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OperationalEvent(BaseModel):
    """Structured operational event payload."""

    event_type: str
    severity: str = "info"
    component: str | None = None
    operation: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None
    code: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)
