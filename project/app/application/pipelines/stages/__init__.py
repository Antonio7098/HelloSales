"""Pipeline stages - building blocks for AI pipelines."""

from app.application.pipelines.stages.base import Stage, StageContext, StageResult
from app.application.pipelines.stages.guard import InputGuardStage, OutputGuardStage
from app.application.pipelines.stages.enrich import ProfileEnrichStage, SummaryEnrichStage
from app.application.pipelines.stages.llm import LLMStage
from app.application.pipelines.stages.persist import PersistStage

__all__ = [
    # Base
    "Stage",
    "StageContext",
    "StageResult",
    # Guards
    "InputGuardStage",
    "OutputGuardStage",
    # Enrichment
    "ProfileEnrichStage",
    "SummaryEnrichStage",
    # LLM
    "LLMStage",
    # Persistence
    "PersistStage",
]
