"""Registry for concrete application agents."""

from __future__ import annotations

from collections.abc import Iterable

from hello_sales_backend.shared.errors import app_error

from .contracts import AgentDefinition


class AgentRegistry:
    """Central lookup for application agent definitions."""

    def __init__(self, definitions: Iterable[AgentDefinition], *, default_agent_id: str) -> None:
        self._definitions = {item.agent_id: item for item in definitions}
        self._default_agent_id = default_agent_id

    def require(self, agent_id: str | None) -> AgentDefinition:
        resolved_id = (agent_id or "").strip() or self._default_agent_id
        definition = self._definitions.get(resolved_id)
        if definition is not None:
            return definition
        raise app_error(
            "Requested agent profile is not registered",
            code="agent.profile.not_found",
            category="validation",
            status_code=404,
            details={"profile_name": resolved_id, "available_profiles": sorted(self._definitions)},
            operation="agent.registry.require",
            component="agent",
        )

    def definitions(self) -> list[AgentDefinition]:
        """Return registered agent definitions in stable order."""

        return [self._definitions[key] for key in sorted(self._definitions)]
