"""Workflow registration primitives."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class WorkflowRegistry:
    """Tracks registered workflow names."""

    names: set[str] = field(default_factory=set)

    def register(self, name: str) -> None:
        self.names.add(name)
