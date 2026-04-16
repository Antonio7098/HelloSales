"""Platform-owned agent runtime contracts."""

from __future__ import annotations

from typing import Protocol

from hello_sales_backend.platform.agents.tools import AgentToolCatalog, AgentToolRequest
from hello_sales_backend.platform.providers.llm.contracts import ChatMessage


class AgentSelectionPolicyPort(Protocol):
    """Select tools for one agent turn."""

    def select(self, user_input: str, catalog: AgentToolCatalog) -> list[AgentToolRequest]: ...


class AgentDefinitionPort(Protocol):
    """Concrete agent profile contract consumed by the runtime."""

    @property
    def agent_id(self) -> str: ...

    @property
    def display_name(self) -> str: ...

    @property
    def tools(self) -> AgentToolCatalog: ...

    @property
    def selection_policy(self) -> AgentSelectionPolicyPort: ...

    def build_messages(self, user_input: str, tool_results: list[str]) -> list[ChatMessage]: ...

    def build_fallback_response(self, user_input: str, tool_results: list[str]) -> str: ...


class AgentDefinitionResolverPort(Protocol):
    """Resolve concrete agent profiles for the runtime."""

    def require(self, agent_id: str | None) -> AgentDefinitionPort: ...


class AgentProfileCatalogPort(Protocol):
    """Expose registered agent profile metadata."""

    def list_profiles(self) -> list[tuple[str, str]]: ...
