"""Shared forward references for substrate protocols."""
from __future__ import annotations

from typing import Protocol


class ContextSnapshot(Protocol):
    """Immutable view passed to Agents and Workers."""
    pass


class PipelineEvent(Protocol):
    """Typed, durably recorded occurrence."""
    pass


class Mutation(Protocol):
    """DB writes, memory updates."""
    pass
