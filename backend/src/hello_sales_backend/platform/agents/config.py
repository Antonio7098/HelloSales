"""Generic agent runtime configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class AgentRuntimeConfig:
    """Resolved generic-agent runtime configuration."""

    default_profile: str = "generic"
    approval_timeout_seconds: int = 3600
    max_event_replay: int = 200
