"""AI orchestration and providers.

This module contains:
- substrate: Core AI infrastructure (pipeline, projector, policy, events, observability)
- agents: Agent layer (router, conversational, tools)
- stages: Project-specific stages
- providers: LLM, STT, TTS provider implementations
"""

from . import stages, substrate

__all__ = [
    "substrate",
    "stages",
]
