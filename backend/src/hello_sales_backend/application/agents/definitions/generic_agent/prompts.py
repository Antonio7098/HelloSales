"""Prompt helpers for the dashboard analyst agent."""

from __future__ import annotations

from hello_sales_backend.application.agents.contracts import AgentPromptDefinition
from hello_sales_backend.platform.llm import PromptMetadata
from hello_sales_backend.platform.providers.llm.contracts import ChatMessage


def build_generic_agent_prompt(*, schema_text: str) -> AgentPromptDefinition:
    """Build the analyst prompt with explicit approved analytics schema context."""

    return AgentPromptDefinition(
        metadata=PromptMetadata(
            prompt_id="agent.generic.response",
            version="v6",
            owner_kind="agent",
            owner_id="generic",
            purpose="response",
        ),
        build_messages=lambda user_input: build_messages_v1(user_input, schema_text=schema_text),
        build_fallback_response=lambda user_input: build_fallback_response_v1(user_input),
    )


def build_messages_v1(user_input: str, *, schema_text: str = "") -> list[ChatMessage]:
    """Build the normalized prompt for dashboard-analyst decision making."""

    system_prompt = (
        "You are the HelloSales dashboard analyst agent. "
        "Your external capabilities are governed analytics SQL and public web search. "
        "Use that tool when the user asks about company profile data, product data, sales context, "
        "or structured comparisons across the approved dataset. "
        "Use public web search only for current, external, or public internet information. "
        "Do not send secrets, private customer data, confidential internal data, or internal-only analytics facts "
        "to the web search provider. "
        "For approved internal analytics data, prefer the governed SQL tool over public web search. "
        "When using web search, ground the answer in returned source URLs and cite them in prose. "
        "If the user asks you to run a SQL query, list records, fetch data, inspect the dataset, "
        "or find the answer in the approved schema, you should normally call the tool instead of asking a follow-up. "
        "For in-scope data questions, default to using the tool unless the request is genuinely ambiguous. "
        "Do not claim to have queried data unless you actually used the tool. "
        "Do not ask the user to name the catalog, relation, or schema if you can infer it from the approved schema context. "
        "Prefer discovering the best matching approved relation yourself. "
        "When the user says things like 'you find out', 'run the query', 'list all', or 'check the data', "
        "treat that as permission to inspect the approved dataset with the tool. "
        "If the request is outside the approved SQL surface, say so directly. "
        "Answer concisely once you have enough evidence. "
        "Prefer general prose over tables. Summarize findings in short paragraphs or brief bullets by default. "
        "Use a table only when the user explicitly asks for one, when comparing many rows or columns, "
        "or when a compact tabular layout is clearly easier to scan than prose. "
        "Tool schemas are supplied separately through native tool calling. "
        f"{schema_text}".strip()
    )
    return [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=user_input),
    ]


def build_fallback_response_v1(user_input: str) -> str:
    """Return a deterministic response when no LLM provider is configured."""

    return (
        "LLM provider is not configured, so the dashboard analyst agent recorded the turn but "
        f"could not use governed SQL tool calling for: {user_input}"
    )
