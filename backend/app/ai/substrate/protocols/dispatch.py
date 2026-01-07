"""Dispatcher protocols - in-kernel, semantic agent/behavior selection."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.ai.substrate.protocols.common import ContextSnapshot


@dataclass(frozen=True)
class DispatchDecision:
    """What the dispatcher decided."""

    agent_id: str  # e.g., "coach_v2", "interviewer", "doc_editor"
    behavior: str  # e.g., "practice", "roleplay", "quiz"
    sub_dispatcher: str | None = None  # For hierarchical dispatch
    path_config: dict[str, Any] = field(default_factory=dict)  # Path-specific overrides
    confidence: float = 1.0
    reason: str | None = None


class Dispatcher(Protocol):
    """Semantic routing INSIDE the kernel.

    Has full context. Selects agent, behavior, and path.
    May use LLM classifier or rules.

    Key insight: Dispatcher has FULL context (enrichments, memory, history)
    unlike Router which runs before enrichment.
    """

    id: str

    async def dispatch(self, snapshot: ContextSnapshot) -> DispatchDecision:
        """Given full context, decide which agent and behavior to use."""
        ...
