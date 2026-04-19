"""Prompt helpers for the observer agent."""

from __future__ import annotations

from hello_sales_backend.application.agents.contracts import AgentPromptDefinition
from hello_sales_backend.platform.llm import PromptMetadata
from hello_sales_backend.platform.providers.llm.contracts import ChatMessage

OBSERVER_AGENT_RESPONSE_PROMPT = AgentPromptDefinition(
    metadata=PromptMetadata(
        prompt_id="agent.observer.response",
        version="v1",
        owner_kind="agent",
        owner_id="observer",
        purpose="response",
    ),
    build_messages=lambda user_input, tool_context: build_messages_v1(user_input, tool_context),
    build_fallback_response=lambda user_input, tool_context: build_fallback_response_v1(
        user_input, tool_context
    ),
)


def build_messages_v1(user_input: str, tool_context: list[str]) -> list[ChatMessage]:
    """Build the prompt set for the observer agent."""

    tool_block = "\n".join(f"- {item}" for item in tool_context) if tool_context else "- no tools were executed"
    system_prompt = (
        "You are the HelloSales observer agent. "
        "Focus on operational visibility, answer tersely, and summarize only what the supplied tool context proves."
    )
    return [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="system", content=f"Observed operational context:\n{tool_block}"),
        ChatMessage(role="user", content=user_input),
    ]


def build_fallback_response_v1(user_input: str, tool_context: list[str]) -> str:
    """Return a deterministic observer response when no LLM provider is configured."""

    if tool_context:
        return "Observer agent fallback summary:\n" + "\n".join(f"- {item}" for item in tool_context)
    return f"Observer agent recorded the request but no observable tools matched: {user_input}"
