"""Application-level agent definition contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from hello_sales_backend.platform.agents.tools import AgentToolCatalog
from hello_sales_backend.platform.llm import (
    ChatMessage,
    EffectivePromptRef,
    PromptMetadata,
    effective_prompt_ref,
)

PromptMessageBuilder = Callable[[str], list[ChatMessage]]
FallbackResponseBuilder = Callable[[str], str]


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
    prompt: AgentPromptDefinition

    def build_messages(self, user_input: str) -> list[ChatMessage]:
        return self.prompt.build_messages(user_input)

    def build_fallback_response(self, user_input: str) -> str:
        return self.prompt.build_fallback_response(user_input)

    def effective_prompt_ref(self) -> EffectivePromptRef:
        return self.prompt.effective_prompt
