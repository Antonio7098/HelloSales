"""Worker protocols - background processing, no user-facing output."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from app.ai.substrate.agent.context_snapshot import ContextSnapshot


@dataclass
class WorkerResult:
    """Worker output - data and side effects only.

    Workers do NOT produce user-facing messages.
    """

    data: dict[str, Any] = field(default_factory=dict)
    events: list = field(default_factory=list)
    mutations: list = field(default_factory=list)


class Worker(Protocol):
    """Background processor - does NOT produce user-facing output.

    Workers are invoked by stages via DAG execution. The triggers attribute
    is deprecated and ignored - execution order is controlled by kernels.json.
    """

    id: str
    triggers: list[str] | None = None

    async def process(self, snapshot: ContextSnapshot) -> WorkerResult:
        """Process context and produce side effects. Does NOT produce user-facing messages."""
        ...


__all__ = ["Worker", "WorkerResult"]
