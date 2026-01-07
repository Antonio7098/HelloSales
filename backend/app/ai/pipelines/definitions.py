"""Concrete pipeline implementations for all Eloquence pipelines.

These classes replace pipelines.json, kernels.json, and channels.json.

Pipelines are registered via register_all_pipelines() which should be called
at application startup after all modules are loaded.
"""

from __future__ import annotations

from app.ai.substrate.stages.base import StageKind
from app.ai.substrate.stages.graph import UnifiedStageSpec
from app.ai.substrate.stages.pipeline import Pipeline, make_runner
from app.ai.substrate.stages.pipeline_registry import pipeline_registry

# Track registration state
_pipelines_registered = False


class ChatFastPipeline(Pipeline):
    """Standard fast chat pipeline with assessment and safety rails."""

    def __init__(self) -> None:
        from app.ai.stages.chat.assessment import AssessmentStage
        from app.ai.stages.chat.context_build import (
            ChatContextBuildStage,
            ChatPersistStage,
            EnricherPrefetchStage,
            SkillsContextStage,
        )
        from app.ai.stages.chat.dispatch import DispatchStage
        from app.ai.stages.chat.llm_stream import LlmStreamStage
        from app.ai.stages.chat.router import RouterStage
        from app.ai.stages.chat.triage import TriageStage
        from app.ai.stages.chat.validation import ValidationStage
        from app.ai.stages.voice import PolicyStage, VoiceGuardrailsStage

        self.stages = {
            "router": UnifiedStageSpec(
                name="router",
                runner=make_runner(RouterStage),
                kind=StageKind.ROUTE,
            ),
            "enricher_prefetch": UnifiedStageSpec(
                name="enricher_prefetch",
                runner=make_runner(EnricherPrefetchStage),
                kind=StageKind.ENRICH,
                dependencies=("router",),
            ),
            "skills_context": UnifiedStageSpec(
                name="skills_context",
                runner=make_runner(SkillsContextStage),
                kind=StageKind.ENRICH,
                dependencies=("router",),
            ),
            "triage": UnifiedStageSpec(
                name="triage",
                runner=make_runner(TriageStage),
                kind=StageKind.WORK,
                dependencies=("skills_context",),
            ),
            "assessment": UnifiedStageSpec(
                name="assessment",
                runner=make_runner(AssessmentStage),
                kind=StageKind.WORK,
                dependencies=("triage",),
                conditional=True,  # Only runs if needed
            ),
            "context_build": UnifiedStageSpec(
                name="context_build",
                runner=make_runner(ChatContextBuildStage),
                kind=StageKind.ENRICH,
                dependencies=("enricher_prefetch", "skills_context"),
            ),
            "dispatch": UnifiedStageSpec(
                name="dispatch",
                runner=make_runner(DispatchStage),
                kind=StageKind.ROUTE,
                dependencies=("context_build",),
            ),
            "guardrails": UnifiedStageSpec(
                name="guardrails",
                runner=make_runner(VoiceGuardrailsStage),
                kind=StageKind.GUARD,
                dependencies=("dispatch",),
            ),
            "policy": UnifiedStageSpec(
                name="policy",
                runner=make_runner(PolicyStage),
                kind=StageKind.GUARD,
                dependencies=("guardrails",),
            ),
            "llm_stream": UnifiedStageSpec(
                name="llm_stream",
                runner=make_runner(LlmStreamStage),
                kind=StageKind.TRANSFORM,
                dependencies=("policy", "context_build"),
            ),
            "validation": UnifiedStageSpec(
                name="validation",
                runner=make_runner(ValidationStage),
                kind=StageKind.GUARD,
                dependencies=("llm_stream",),
            ),
            "post_llm_policy": UnifiedStageSpec(
                name="post_llm_policy",
                runner=make_runner(PolicyStage),
                kind=StageKind.GUARD,
                dependencies=("validation",),
            ),
            "persist": UnifiedStageSpec(
                name="persist",
                runner=make_runner(ChatPersistStage),
                kind=StageKind.WORK,
                dependencies=("llm_stream", "post_llm_policy"),
            ),
        }


class ChatAccuratePipeline(Pipeline):
    """Accurate chat pipeline where assessment runs before LLM generation."""

    def __init__(self) -> None:
        # Same as ChatFast but assessment is NOT conditional
        from app.ai.stages.chat.assessment import AssessmentStage
        from app.ai.stages.chat.context_build import (
            ChatContextBuildStage,
            ChatPersistStage,
            EnricherPrefetchStage,
            SkillsContextStage,
        )
        from app.ai.stages.chat.dispatch import DispatchStage
        from app.ai.stages.chat.llm_stream import LlmStreamStage
        from app.ai.stages.chat.router import RouterStage
        from app.ai.stages.chat.triage import TriageStage
        from app.ai.stages.chat.validation import ValidationStage
        from app.ai.stages.voice import PolicyStage, VoiceGuardrailsStage

        self.stages = {
            "router": UnifiedStageSpec(
                name="router",
                runner=make_runner(RouterStage),
                kind=StageKind.ROUTE,
            ),
            "enricher_prefetch": UnifiedStageSpec(
                name="enricher_prefetch",
                runner=make_runner(EnricherPrefetchStage),
                kind=StageKind.ENRICH,
                dependencies=("router",),
            ),
            "skills_context": UnifiedStageSpec(
                name="skills_context",
                runner=make_runner(SkillsContextStage),
                kind=StageKind.ENRICH,
                dependencies=("router",),
            ),
            "triage": UnifiedStageSpec(
                name="triage",
                runner=make_runner(TriageStage),
                kind=StageKind.WORK,
                dependencies=("skills_context",),
            ),
            "assessment": UnifiedStageSpec(
                name="assessment",
                runner=make_runner(AssessmentStage),
                kind=StageKind.WORK,
                dependencies=("triage",),
                conditional=False,  # Always runs in accurate mode
            ),
            "context_build": UnifiedStageSpec(
                name="context_build",
                runner=make_runner(ChatContextBuildStage),
                kind=StageKind.ENRICH,
                dependencies=("enricher_prefetch", "skills_context"),
            ),
            "dispatch": UnifiedStageSpec(
                name="dispatch",
                runner=make_runner(DispatchStage),
                kind=StageKind.ROUTE,
                dependencies=("context_build",),
            ),
            "guardrails": UnifiedStageSpec(
                name="guardrails",
                runner=make_runner(VoiceGuardrailsStage),
                kind=StageKind.GUARD,
                dependencies=("dispatch",),
            ),
            "policy": UnifiedStageSpec(
                name="policy",
                runner=make_runner(PolicyStage),
                kind=StageKind.GUARD,
                dependencies=("guardrails",),
            ),
            "llm_stream": UnifiedStageSpec(
                name="llm_stream",
                runner=make_runner(LlmStreamStage),
                kind=StageKind.TRANSFORM,
                dependencies=("policy", "context_build"),
            ),
            "validation": UnifiedStageSpec(
                name="validation",
                runner=make_runner(ValidationStage),
                kind=StageKind.GUARD,
                dependencies=("llm_stream",),
            ),
            "post_llm_policy": UnifiedStageSpec(
                name="post_llm_policy",
                runner=make_runner(PolicyStage),
                kind=StageKind.GUARD,
                dependencies=("validation",),
            ),
            "persist": UnifiedStageSpec(
                name="persist",
                runner=make_runner(ChatPersistStage),
                kind=StageKind.WORK,
                dependencies=("llm_stream", "post_llm_policy"),
            ),
        }


class VoiceFastPipeline(Pipeline):
    """Fast voice pipeline with STT, conditional assessment, and TTS."""

    def __init__(self) -> None:
        from app.ai.stages.chat.assessment import AssessmentStage
        from app.ai.stages.chat.context_build import (
            ChatContextBuildStage,
            ChatPersistStage,
            EnricherPrefetchStage,
            SkillsContextStage,
        )
        from app.ai.stages.chat.dispatch import DispatchStage
        from app.ai.stages.chat.llm_stream import LlmStreamStage
        from app.ai.stages.chat.triage import TriageStage
        from app.ai.stages.chat.validation import ValidationStage
        from app.ai.stages.voice import (
            PolicyStage,
            SttStage,
            TtsIncrementalStage,
            UserMessagePersistStage,
            VoiceGuardrailsStage,
            VoiceInputStage,
        )

        self.stages = {
            "voice_input": UnifiedStageSpec(
                name="voice_input",
                runner=make_runner(VoiceInputStage),
                kind=StageKind.TRANSFORM,
            ),
            "stt": UnifiedStageSpec(
                name="stt",
                runner=make_runner(SttStage),
                kind=StageKind.TRANSFORM,
                dependencies=("voice_input",),
            ),
            "user_message_persist": UnifiedStageSpec(
                name="user_message_persist",
                runner=make_runner(UserMessagePersistStage),
                kind=StageKind.WORK,
                dependencies=("stt",),
            ),
            "enricher_prefetch": UnifiedStageSpec(
                name="enricher_prefetch",
                runner=make_runner(EnricherPrefetchStage),
                kind=StageKind.ENRICH,
                dependencies=("stt",),
            ),
            "skills_context": UnifiedStageSpec(
                name="skills_context",
                runner=make_runner(SkillsContextStage),
                kind=StageKind.ENRICH,
                dependencies=("stt",),
            ),
            "triage": UnifiedStageSpec(
                name="triage",
                runner=make_runner(TriageStage),
                kind=StageKind.WORK,
                dependencies=("skills_context",),
            ),
            "assessment": UnifiedStageSpec(
                name="assessment",
                runner=make_runner(AssessmentStage),
                kind=StageKind.WORK,
                dependencies=("triage",),
                conditional=True,  # Conditional in fast mode
            ),
            "context_build": UnifiedStageSpec(
                name="context_build",
                runner=make_runner(ChatContextBuildStage),
                kind=StageKind.ENRICH,
                dependencies=("enricher_prefetch", "skills_context", "stt"),
            ),
            "dispatch": UnifiedStageSpec(
                name="dispatch",
                runner=make_runner(DispatchStage),
                kind=StageKind.ROUTE,
                dependencies=("context_build",),
            ),
            "guardrails": UnifiedStageSpec(
                name="guardrails",
                runner=make_runner(VoiceGuardrailsStage),
                kind=StageKind.GUARD,
                dependencies=("dispatch", "stt"),
            ),
            "policy": UnifiedStageSpec(
                name="policy",
                runner=make_runner(PolicyStage),
                kind=StageKind.GUARD,
                dependencies=("guardrails",),
            ),
            "llm_stream": UnifiedStageSpec(
                name="llm_stream",
                runner=make_runner(LlmStreamStage),
                kind=StageKind.TRANSFORM,
                dependencies=("policy", "context_build"),
            ),
            "validation": UnifiedStageSpec(
                name="validation",
                runner=make_runner(ValidationStage),
                kind=StageKind.GUARD,
                dependencies=("llm_stream",),
            ),
            "post_llm_policy": UnifiedStageSpec(
                name="post_llm_policy",
                runner=make_runner(PolicyStage),
                kind=StageKind.GUARD,
                dependencies=("validation",),
            ),
            "persist": UnifiedStageSpec(
                name="persist",
                runner=make_runner(ChatPersistStage),
                kind=StageKind.WORK,
                dependencies=("llm_stream", "post_llm_policy", "user_message_persist"),
            ),
            "tts_incremental": UnifiedStageSpec(
                name="tts_incremental",
                runner=make_runner(TtsIncrementalStage),
                kind=StageKind.TRANSFORM,
                dependencies=("llm_stream",),
            ),
        }


class VoiceAccuratePipeline(Pipeline):
    """Accurate voice pipeline where assessment runs before LLM generation."""

    def __init__(self) -> None:
        # Same structure as VoiceFast but assessment is NOT conditional
        from app.ai.stages.chat.assessment import AssessmentStage
        from app.ai.stages.chat.context_build import (
            ChatContextBuildStage,
            ChatPersistStage,
            EnricherPrefetchStage,
            SkillsContextStage,
        )
        from app.ai.stages.chat.dispatch import DispatchStage
        from app.ai.stages.chat.llm_stream import LlmStreamStage
        from app.ai.stages.chat.triage import TriageStage
        from app.ai.stages.chat.validation import ValidationStage
        from app.ai.stages.voice import (
            PolicyStage,
            SttStage,
            TtsIncrementalStage,
            UserMessagePersistStage,
            VoiceGuardrailsStage,
            VoiceInputStage,
        )

        self.stages = {
            "voice_input": UnifiedStageSpec(
                name="voice_input",
                runner=make_runner(VoiceInputStage),
                kind=StageKind.TRANSFORM,
            ),
            "stt": UnifiedStageSpec(
                name="stt",
                runner=make_runner(SttStage),
                kind=StageKind.TRANSFORM,
                dependencies=("voice_input",),
            ),
            "user_message_persist": UnifiedStageSpec(
                name="user_message_persist",
                runner=make_runner(UserMessagePersistStage),
                kind=StageKind.WORK,
                dependencies=("stt",),
            ),
            "enricher_prefetch": UnifiedStageSpec(
                name="enricher_prefetch",
                runner=make_runner(EnricherPrefetchStage),
                kind=StageKind.ENRICH,
                dependencies=("stt",),
            ),
            "skills_context": UnifiedStageSpec(
                name="skills_context",
                runner=make_runner(SkillsContextStage),
                kind=StageKind.ENRICH,
                dependencies=("stt",),
            ),
            "triage": UnifiedStageSpec(
                name="triage",
                runner=make_runner(TriageStage),
                kind=StageKind.WORK,
                dependencies=("skills_context",),
            ),
            "assessment": UnifiedStageSpec(
                name="assessment",
                runner=make_runner(AssessmentStage),
                kind=StageKind.WORK,
                dependencies=("triage",),
                conditional=False,  # Always runs in accurate mode
            ),
            "context_build": UnifiedStageSpec(
                name="context_build",
                runner=make_runner(ChatContextBuildStage),
                kind=StageKind.ENRICH,
                dependencies=("enricher_prefetch", "skills_context", "stt"),
            ),
            "dispatch": UnifiedStageSpec(
                name="dispatch",
                runner=make_runner(DispatchStage),
                kind=StageKind.ROUTE,
                dependencies=("context_build",),
            ),
            "guardrails": UnifiedStageSpec(
                name="guardrails",
                runner=make_runner(VoiceGuardrailsStage),
                kind=StageKind.GUARD,
                dependencies=("dispatch", "stt"),
            ),
            "policy": UnifiedStageSpec(
                name="policy",
                runner=make_runner(PolicyStage),
                kind=StageKind.GUARD,
                dependencies=("guardrails",),
            ),
            "llm_stream": UnifiedStageSpec(
                name="llm_stream",
                runner=make_runner(LlmStreamStage),
                kind=StageKind.TRANSFORM,
                dependencies=("policy", "context_build"),
            ),
            "validation": UnifiedStageSpec(
                name="validation",
                runner=make_runner(ValidationStage),
                kind=StageKind.GUARD,
                dependencies=("llm_stream",),
            ),
            "post_llm_policy": UnifiedStageSpec(
                name="post_llm_policy",
                runner=make_runner(PolicyStage),
                kind=StageKind.GUARD,
                dependencies=("validation",),
            ),
            "persist": UnifiedStageSpec(
                name="persist",
                runner=make_runner(ChatPersistStage),
                kind=StageKind.WORK,
                dependencies=("llm_stream", "post_llm_policy", "user_message_persist"),
            ),
            "tts_incremental": UnifiedStageSpec(
                name="tts_incremental",
                runner=make_runner(TtsIncrementalStage),
                kind=StageKind.TRANSFORM,
                dependencies=("llm_stream",),
            ),
        }


def register_all_pipelines() -> None:
    """Register all pipelines with the global registry.

    Call this at application startup to register all pipelines.
    This function is idempotent - calling it multiple times has no effect.
    """
    global _pipelines_registered
    if _pipelines_registered:
        return

    pipeline_registry.register("chat_fast", ChatFastPipeline())
    pipeline_registry.register("chat_accurate", ChatAccuratePipeline())
    pipeline_registry.register("voice_fast", VoiceFastPipeline())
    pipeline_registry.register("voice_accurate", VoiceAccuratePipeline())

    _pipelines_registered = True


__all__ = [
    "ChatFastPipeline",
    "ChatAccuratePipeline",
    "VoiceFastPipeline",
    "VoiceAccuratePipeline",
    "register_all_pipelines",
]
