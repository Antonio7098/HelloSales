"""Application-level agent definition contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from hello_sales_backend.platform.agents.tools import AgentToolCatalog, AgentToolRequest
from hello_sales_backend.platform.llm import (
    ChatMessage,
    EffectivePromptRef,
    PromptMetadata,
    effective_prompt_ref,
)


class ToolSelectionPolicy(Protocol):
    """Select tools for one agent turn."""

    def select(self, user_input: str, catalog: AgentToolCatalog) -> list[AgentToolRequest]: ...


PromptMessageBuilder = Callable[[str, list[str]], list[ChatMessage]]
FallbackResponseBuilder = Callable[[str, list[str]], str]


@dataclass(slots=True, frozen=True)
class AgentPromptDefinition:
    """First-class prompt definition for one agent capability."""

    metadata: PromptMetadata
    build_messages: PromptMessageBuilder
    build_fallback_response: FallbackResponseBuilder

    @property
    def effective_prompt(self) -> EffectivePromptRef:
        return effective_prompt_ref(self.metadata)


@dataclass(slots=True, frozen=True)
class AgentDefinition:
    """Concrete application agent configuration."""

    agent_id: str
    display_name: str
    tools: AgentToolCatalog
    selection_policy: ToolSelectionPolicy
    prompt: AgentPromptDefinition

    def build_messages(self, user_input: str, tool_results: list[str]) -> list[ChatMessage]:
        return self.prompt.build_messages(user_input, tool_results)

    def build_fallback_response(self, user_input: str, tool_results: list[str]) -> str:
        return self.prompt.build_fallback_response(user_input, tool_results)

    def effective_prompt_ref(self) -> EffectivePromptRef:
        return self.prompt.effective_prompt
