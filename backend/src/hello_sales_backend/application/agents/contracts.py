"""Application-level agent definition contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from hello_sales_backend.platform.agents.tools import AgentToolCatalog, AgentToolRequest
from hello_sales_backend.platform.providers.llm.contracts import ChatMessage


class ToolSelectionPolicy(Protocol):
    """Select tools for one agent turn."""

    def select(self, user_input: str, catalog: AgentToolCatalog) -> list[AgentToolRequest]: ...


PromptMessageBuilder = Callable[[str, list[str]], list[ChatMessage]]
FallbackResponseBuilder = Callable[[str, list[str]], str]


@dataclass(slots=True, frozen=True)
class AgentDefinition:
    """Concrete application agent configuration."""

    agent_id: str
    display_name: str
    tools: AgentToolCatalog
    selection_policy: ToolSelectionPolicy
    build_messages: PromptMessageBuilder
    build_fallback_response: FallbackResponseBuilder
