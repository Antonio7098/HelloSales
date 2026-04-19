"""Prompt helpers for the baseline generic agent."""

from __future__ import annotations

from hello_sales_backend.application.agents.contracts import AgentPromptDefinition
from hello_sales_backend.platform.llm import PromptMetadata
from hello_sales_backend.platform.providers.llm.contracts import ChatMessage

GENERIC_AGENT_RESPONSE_PROMPT = AgentPromptDefinition(
    metadata=PromptMetadata(
        prompt_id="agent.generic.response",
        version="v1",
        owner_kind="agent",
        owner_id="generic",
        purpose="response",
    ),
    build_messages=lambda user_input, tool_context: build_messages_v1(user_input, tool_context),
    build_fallback_response=lambda user_input, tool_context: build_fallback_response_v1(
        user_input, tool_context
    ),
)


def build_messages_v1(user_input: str, tool_context: list[str]) -> list[ChatMessage]:
    """Build the normalized prompt for generic-agent response generation."""

    tool_block = "\n".join(f"- {item}" for item in tool_context) if tool_context else "- no tools were executed"
    system_prompt = (
        "You are the HelloSales generic operational agent. "
        "Answer concisely, rely on the provided tool context when available, "
        "and do not invent runtime state that was not supplied."
    )
    return [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="system", content=f"Operational tool context:\n{tool_block}"),
        ChatMessage(role="user", content=user_input),
    ]


def build_fallback_response_v1(user_input: str, tool_context: list[str]) -> str:
    """Return a deterministic response when no LLM provider is configured."""

    if tool_context:
        context_text = "\n".join(f"- {item}" for item in tool_context)
        return (
            "LLM provider is not configured, so this response was generated from tool results only.\n"
            f"User input: {user_input}\n"
            f"Tool context:\n{context_text}"
        )
    return (
        "LLM provider is not configured and no tools matched this request. "
        "The generic agent recorded the turn but could not produce a richer answer."
    )
