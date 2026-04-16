"""Platform-owned workflow pipeline abstraction."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class WorkflowStageKind(StrEnum):
    """Logical stage kinds understood by the platform workflow wrapper."""

    GUARD = "guard"
    WORK = "work"
    TRANSFORM = "transform"


@dataclass(slots=True, frozen=True)
class WorkflowStageSpec:
    """Platform-owned workflow stage definition."""

    name: str
    handler: Callable[[Any], Awaitable[dict[str, object]]]
    kind: WorkflowStageKind
    dependencies: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class WorkflowStageOutput:
    """Normalized workflow stage output."""

    data: dict[str, object]


class WorkflowPipeline(Protocol):
    """Executable workflow pipeline."""

    async def run(self) -> dict[str, WorkflowStageOutput]: ...


class WorkflowPipelineFactory(Protocol):
    """Build platform-owned workflow pipelines."""

    def create_pipeline(self, *, name: str, stages: list[WorkflowStageSpec]) -> WorkflowPipeline: ...
