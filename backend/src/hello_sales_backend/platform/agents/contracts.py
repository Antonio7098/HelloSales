"""Platform-owned agent runtime contracts."""

from __future__ import annotations

from typing import Protocol

from hello_sales_backend.platform.agents.tools import AgentToolCatalog
from hello_sales_backend.platform.llm import ChatMessage, EffectivePromptRef


class AgentDefinitionPort(Protocol):
    """Concrete agent profile contract consumed by the runtime."""

    @property
    def agent_id(self) -> str: ...

    @property
    def display_name(self) -> str: ...

    @property
    def tools(self) -> AgentToolCatalog: ...

    @property
    def prompt(self) -> object: ...

    def build_messages(self, user_input: str) -> list[ChatMessage]: ...

    def build_fallback_response(self, user_input: str) -> str: ...

    def effective_prompt_ref(self) -> EffectivePromptRef: ...


class AgentDefinitionResolverPort(Protocol):
    """Resolve concrete agent profiles for the runtime."""

    def require(self, agent_id: str | None) -> AgentDefinitionPort: ...


class AgentProfileCatalogPort(Protocol):
    """Expose registered agent profile metadata."""

    def list_profiles(self) -> list[tuple[str, str]]: ...
