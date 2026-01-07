"""Agent layer package - concrete agent implementations."""

from app.ai.agents.conversational import ConversationalAgent
from app.ai.substrate.agent import (
    Action,
    ActionType,
    AgentError,
    AgentPlan,
    AgentRequest,
    Artifact,
    BaseAgent,
    Plan,
    RoutingPlan,
)

__all__ = [
    "AgentRequest",
    "AgentPlan",  # Backwards compatibility alias for RoutingPlan
    "RoutingPlan",
    "Plan",
    "Action",
    "Artifact",
    "BaseAgent",
    "AgentError",
    "ActionType",
    "ConversationalAgent",
]
