"""Agent protocols - main interactor with user, doing actions and streaming.

Agents are the primary conversational component in the pipeline. They:
- Receive a ContextSnapshot (full context including messages, enrichments)
- Plan a response (assistant message, actions to execute, artifacts to emit)
- Optionally stream output incrementally

Agents differ from other primitives:
- Worker: Background processing, produces side effects only, no user output
- Dispatcher: Selects agent/behavior inside kernel
- Router: Selects topology before kernel (no enrichments)
- Agent: Main interactor, produces user-facing message + actions + artifacts

Key characteristics:
- Produces user-facing output (assistant_message)
- Can request actions to be executed by tool system
- Can produce artifacts for UI rendering
- Has streaming support (via yield in streaming implementations)

Services vs Capabilities:
- services: Which service types this agent supports (e.g., "chat", "voice")
- capabilities: Which action types this agent can execute
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.ai.substrate.agent.context_snapshot import ContextSnapshot

    # Import from agent.types directly to avoid circular import
    from app.ai.substrate.agent.types import (
        ActionType,
        AgentRequest,
        Plan,
    )


class Agent(ABC):
    """Protocol for conversational agents.

    Agents are the primary component that interacts with users by:
    1. Analyzing ContextSnapshot (full context with enrichments)
    2. Planning a response containing assistant message, actions, and artifacts
    3. Optionally streaming output incrementally

    Key characteristics:
    - Produces user-facing output (assistant_message)
    - Can request actions to be executed by the tool system
    - Can produce artifacts for UI rendering
    - Has streaming support (via yield in streaming implementations)

    Services vs Capabilities:
    - services: Which service types this agent supports (e.g., "chat", "voice")
    - capabilities: Which action types this agent can execute
    """

    id: str  # Unique identifier for this agent (e.g., "coach_v2", "interviewer")

    services: tuple[str, ...] = ()  # Services this agent can handle
    capabilities: tuple[str, ...] = ()  # Action types this agent can execute

    def supports(self, request: AgentRequest) -> bool:
        """Check if this agent can handle the given request.

        Args:
            request: The routing request with service type

        Returns:
            True if agent supports the request's service
        """
        return request.service in self.services

    def can_execute(self, action_type: ActionType) -> bool:
        """Check if this agent can execute the given action type.

        Args:
            action_type: The type of action to execute

        Returns:
            True if this agent has the capability to execute this action
        """
        return action_type in self.capabilities

    @abstractmethod
    async def plan(self, snapshot: ContextSnapshot) -> Plan:
        """Produce a Plan for the given context.

        The agent analyzes the ContextSnapshot (which contains:
        - Message history
        - User input
        - Enrichments (profile, skills, memory, documents, web results)
        - Routing decision
        - Assessment state

        The agent decides:
        1. What message to show the user (assistant_message)
        2. What actions to request (if any)
        3. What artifacts to produce (if any)
        4. Whether to re-enter after actions complete (requires_reentry)

        Args:
            snapshot: Full context snapshot with enrichments

        Returns:
            Plan containing the agent's response
        """
        ...

    def describe(self) -> dict[str, Any]:
        """Return metadata for debugging and diagnostics.

        Returns:
            Dict with agent metadata (id, services, capabilities)
        """
        return {
            "id": self.id,
            "services": self.services,
            "capabilities": self.capabilities,
        }


class StreamingAgent(ABC):
    """Protocol for streaming agents.

    Streaming agents yield output incrementally instead of waiting
    for a full response to be generated.

    Streaming is useful for:
    - Reducing perceived latency
    - Supporting real-time feedback
    - Handling long responses gracefully

    The streaming agent should yield Plan objects with partial
    assistant_message as output builds up.
    """

    id: str

    services: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()

    def supports(self, request: AgentRequest) -> bool:
        """Check if this agent can handle the given request."""
        return request.service in self.services

    def can_execute(self, action_type: ActionType) -> bool:
        """Check if this agent can execute the given action type."""
        return action_type in self.capabilities

    @abstractmethod
    async def plan(self, snapshot: ContextSnapshot):
        """Stream plans incrementally.

        Yields partial Plan objects as output builds up.

        Args:
            snapshot: Full context snapshot with enrichments

        Yields:
            Partial Plan objects with assistant_message populated incrementally
        """
        ...

    def describe(self) -> dict[str, Any]:
        """Return metadata for debugging and diagnostics."""
        return {
            "id": self.id,
            "services": self.services,
            "capabilities": self.capabilities,
        }


__all__ = ["Agent", "StreamingAgent"]

