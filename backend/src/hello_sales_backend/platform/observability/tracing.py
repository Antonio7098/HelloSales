"""Trace metadata primitives."""

from pydantic import BaseModel


class TraceContext(BaseModel):
    """Trace metadata used across tasks and workflows."""

    request_id: str | None = None
    trace_id: str | None = None
    actor_id: str | None = None
