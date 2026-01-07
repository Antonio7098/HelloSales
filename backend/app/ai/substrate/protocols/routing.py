"""Routing protocols - pre-kernel, deterministic topology selection."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True)
class RouteRequest:
    """Minimal info needed for routing.

    Router runs BEFORE kernel execution. No enrichments available.
    Should NOT call LLM (or use fast/cheap classifier only).
    """

    service: str  # "chat", "voice"
    input_text: str | None  # User message (may be None for voice)
    input_metadata: dict[str, Any]  # Platform, client hints
    user_id: UUID
    session_id: UUID
    org_id: UUID | None = None


@dataclass(frozen=True)
class RouteDecision:
    """Topology selection output from router."""

    topology: str  # e.g., "chat_fast", "voice_accurate"
    kernel: str  # e.g., "fast_kernel", "accurate_kernel"
    channel: str  # e.g., "voice_channel", "text_channel"
    agent_id: str  # e.g., "coach_v2"
    behavior: str  # e.g., "practice", "roleplay"
    confidence: float = 1.0
    reason: str | None = None


class Router(Protocol):
    """Selects topology - runs BEFORE kernel execution.

    Characteristics:
    - Fast, deterministic, no LLM involvement (or tiny classifier only)
    - No enrichments available
    - Deterministic given same inputs
    - Can be rules-based, embedding-based, or small model
    """

    id: str

    def route(self, request: RouteRequest) -> RouteDecision:
        """Lightweight, deterministic routing decision."""
        ...
