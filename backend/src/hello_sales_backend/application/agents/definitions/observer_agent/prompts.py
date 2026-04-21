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
    build_messages=lambda user_input: build_messages_v1(user_input),
    build_fallback_response=lambda user_input: build_fallback_response_v1(user_input),
)


def build_messages_v1(user_input: str) -> list[ChatMessage]:
    """Build the prompt set for the observer agent."""

    system_prompt = (
        "You are the HelloSales observer agent. "
        "Focus on operational visibility, use only the provided read-only tools, "
        "and summarize only what the tool results prove. "
        "Tool schemas are supplied separately through native tool calling."
    )
    return [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=user_input),
    ]


def build_fallback_response_v1(user_input: str) -> str:
    """Return a deterministic observer response when no LLM provider is configured."""

    return f"Observer agent recorded the request but native tool calling is unavailable: {user_input}"
