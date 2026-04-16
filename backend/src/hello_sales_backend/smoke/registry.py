"""Central registry of smoke suites."""

from __future__ import annotations

from collections.abc import Iterable

from hello_sales_backend.shared.errors import app_error

from .contracts import SmokeCase, SmokeDefinition


class SmokeRegistry:
    """Registry used by the CLI and tests to discover smoke suites."""

    def __init__(self, smokes: Iterable[SmokeCase] | None = None) -> None:
        self._smokes: dict[str, SmokeCase] = {}
        for smoke in smokes or ():
            self.register(smoke)

    def register(self, smoke: SmokeCase) -> None:
        if smoke.name in self._smokes:
            raise ValueError(f"Smoke '{smoke.name}' is already registered")
        self._smokes[smoke.name] = smoke

    def get(self, name: str) -> SmokeCase:
        smoke = self._smokes.get(name)
        if smoke is not None:
            return smoke
        raise app_error(
            "Unknown smoke target",
            code="smoke.target.unknown",
            category="validation",
            status_code=400,
            details={"smoke_name": name, "available_smokes": self.names()},
            operation="smoke.registry.get",
            component="smoke",
        )

    def default(self) -> SmokeCase:
        if not self._smokes:
            raise RuntimeError("Smoke registry is empty")
        return next(iter(self._smokes.values()))

    def definitions(self) -> list[SmokeDefinition]:
        return [
            SmokeDefinition(name=smoke.name, description=smoke.description)
            for smoke in self._smokes.values()
        ]

    def names(self) -> list[str]:
        return list(self._smokes)
