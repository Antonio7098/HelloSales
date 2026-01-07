"""Default conversational agent implementation.

This agent handles basic chat and voice interactions. It is responsible for:
1. Analyzing the context snapshot
2. Producing a user-facing response (Plan.assistant_message)
3. Requesting any necessary actions (Plan.actions)
4. Producing any UI artifacts (Plan.artifacts)

For routing decisions (topology/behavior selection), see the Router protocol
in substrate/protocols/routing.py
"""
from __future__ import annotations

from app.ai.substrate.agent import (
    Action,
    BaseAgent,
    ContextSnapshot,
    Plan,
)
from app.ai.substrate.agent.agent_registry import register_agent


@register_agent(name="conversational", description="Basic conversational agent for chat and voice")
class ConversationalAgent(BaseAgent):
    """Simple conversational agent that produces basic chat responses.

    This agent:
    - Analyzes the context snapshot
    - Produces a user-facing message
    - Does NOT handle routing (topology/behavior selection) - that's the Router's job
    - Can request actions if needed (e.g., store memory, switch topology)

    The separation follows Stageflow architecture:
    - Router: Pre-kernel, selects topology (fast, no LLM)
    - Dispatcher: In-kernel, selects agent + behavior
    - Agent: Produces Plan (message, actions, artifacts)
    """

    id = "agent.conversational.v1"
    services = ("chat", "voice")
    capabilities = ("respond", "store_memory", "switch_behavior")

    async def plan(self, snapshot: ContextSnapshot) -> Plan:
        """Produce a plan for the given conversation context.

        This method:
        1. Analyzes the user's message
        2. Produces an appropriate response
        3. Determines if any actions are needed
        4. Returns a Plan with message, actions, and artifacts

        Args:
            snapshot: The conversation context including messages, profile, etc.

        Returns:
            Plan with assistant_message, actions, and artifacts
        """
        # Get the latest user message
        user_message = self._get_last_user_message(snapshot)

        # Determine behavior from context
        behavior = snapshot.behavior or "respond"

        # Generate the response based on behavior
        response = self._generate_response(snapshot, user_message, behavior)

        # Build the plan
        plan = Plan(
            assistant_message=response,
            actions=self._determine_actions(snapshot, behavior),
            artifacts=[],
            requires_reentry=self._needs_reentry(snapshot, behavior),
        )

        return plan

    def _get_last_user_message(self, snapshot: ContextSnapshot) -> str:
        """Extract the last user message from the context."""
        for message in reversed(snapshot.messages):
            if message.role == "user":
                return message.content
        return snapshot.input_text or ""

    def _generate_response(
        self, _snapshot: ContextSnapshot, user_message: str, behavior: str
    ) -> str:
        """Generate the assistant's response based on context and behavior.

        This is a placeholder for the actual LLM call. In a real implementation,
        this would call the LLM with the conversation context and system prompt.
        """
        # Placeholder response - in reality, this calls the LLM
        behavior_responses = {
            "respond": f"I understand you said: {user_message}",
            "practice": f"Let's practice! You said: {user_message}",
            "roleplay": f"[Roleplay mode] You said: {user_message}",
            "assessment": f"[Assessment mode] You said: {user_message}",
        }

        return behavior_responses.get(behavior, f"You said: {user_message}")

    def _determine_actions(
        self, snapshot: ContextSnapshot, behavior: str
    ) -> list[Action]:
        """Determine what actions (if any) should be requested."""
        actions = []

        # Example: Store memory for significant interactions
        if behavior == "respond" and snapshot.memory and snapshot.memory.key_facts:
            actions.append(
                    Action(
                        type="store_memory",
                        payload={"facts": snapshot.memory.key_facts},
                    )
                )

        # Example: Switch behavior if requested
        if snapshot.metadata.get("switch_behavior"):
            actions.append(
                Action(
                    type="switch_behavior",
                    payload={"new_behavior": snapshot.metadata["switch_behavior"]},
                )
            )

        return actions

    def _needs_reentry(self, snapshot: ContextSnapshot, behavior: str) -> bool:
        """Determine if the agent should be re-invoked after actions."""
        # For actions that require approval or external processing
        for action in self._determine_actions(snapshot, behavior):
            if action.requires_approval:
                return True
        return False


# =============================================================================
# Routing Helper (for backwards compatibility with existing Router usage)
# =============================================================================

def determine_topology(service: str | None, behavior: str | None) -> str:
    """Determine topology from service and behavior hints.

    This is a helper function that can be used by Routers to determine
    the appropriate topology based on service and behavior.
    """
    service = service or "chat"
    behavior = behavior or "fast"

    if behavior in ("accurate", "accurate_filler"):
        return f"{service}_accurate"
    return f"{service}_fast"


def determine_behavior(topology: str, explicit_behavior: str | None) -> str:
    """Determine behavior from topology and explicit request.

    This is a helper function that can be used by Dispatchers to determine
    the appropriate behavior.
    """
    if explicit_behavior:
        return explicit_behavior

    if "accurate" in topology:
        return "accurate"
    return "respond"


__all__ = ["ConversationalAgent", "determine_topology", "determine_behavior"]
