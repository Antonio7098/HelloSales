"""Prompt helpers for the baseline generic agent."""

from __future__ import annotations

from hello_sales_backend.application.agents.contracts import AgentPromptDefinition
from hello_sales_backend.platform.llm import PromptMetadata
from hello_sales_backend.platform.providers.llm.contracts import ChatMessage

GENERIC_AGENT_RESPONSE_PROMPT = AgentPromptDefinition(
    metadata=PromptMetadata(
        prompt_id="agent.generic.response",
        version="v2",
        owner_kind="agent",
        owner_id="generic",
        purpose="response",
    ),
    build_messages=lambda user_input: build_messages_v1(user_input),
    build_fallback_response=lambda user_input: build_fallback_response_v1(user_input),
)


def build_messages_v1(user_input: str) -> list[ChatMessage]:
    """Build the normalized prompt for generic-agent decision making."""

    system_prompt = (
        "You are the HelloSales generic operational agent. "
        "Use the provided native tools whenever you need live runtime state, "
        "use the governed analytics SQL tool for approved analytics questions, "
        "do not invent tool results, and answer concisely once you have enough evidence. "
        "Tool schemas are supplied separately through native tool calling."
    )
    return [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=user_input),
    ]


def build_fallback_response_v1(user_input: str) -> str:
    """Return a deterministic response when no LLM provider is configured."""

    return (
        "LLM provider is not configured, so the generic agent recorded the turn but could not "
        f"use native tool calling for: {user_input}"
    )
