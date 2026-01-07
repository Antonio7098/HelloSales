"""Agent module - ContextSnapshot for backward compatibility.

Most agent types have been moved to stages/agent.py:
- Action, ActionType -> from app.ai.substrate.stages.agent
- ToolExecutor, ToolRegistry -> from app.ai.substrate.stages.agent
- Artifact -> from app.ai.substrate.stages.base (as StageArtifact)

This module only exports ContextSnapshot which is still widely used.
"""

from app.ai.substrate.agent.context_snapshot import (
    ContextSnapshot,
    DocumentEnrichment,
    MemoryEnrichment,
    Message,
    ProfileEnrichment,
    RoutingDecision,
    SkillsEnrichment,
)

__all__ = [
    "ContextSnapshot",
    "DocumentEnrichment",
    "MemoryEnrichment",
    "Message",
    "ProfileEnrichment",
    "RoutingDecision",
    "SkillsEnrichment",
]
