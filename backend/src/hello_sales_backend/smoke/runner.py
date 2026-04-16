"""Centralized smoke runner."""

from __future__ import annotations

from .contracts import SmokeContext, SmokeDefinition, SmokeExecutionResult
from .registry import SmokeRegistry


class SmokeRunner:
    """Execute registered smoke suites against a shared context."""

    def __init__(self, registry: SmokeRegistry, context: SmokeContext) -> None:
        self._registry = registry
        self._context = context

    async def run(self, smoke_name: str | None = None) -> SmokeExecutionResult:
        smoke = self._registry.default() if smoke_name is None else self._registry.get(smoke_name)
        result = await smoke.run(self._context)
        return SmokeExecutionResult.from_result(smoke, result)

    def definitions(self) -> list[SmokeDefinition]:
        return self._registry.definitions()
