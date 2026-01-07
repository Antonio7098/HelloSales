"""Adapter implementations that bridge existing services to formal port interfaces.

These adapters wrap existing concrete services to implement the formal port interfaces,
enabling dependency inversion while maintaining backward compatibility.
"""

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.ports import (
    AssessmentPort,
    ChatPort,
    GuardrailsPort,
    LlmPort,
    LlmRequest,
    LlmResponse,
    PolicyPort,
    SttPort,
    TriagePort,
    TtsPort,
)

if TYPE_CHECKING:
    from app.ai.providers.base import (
        LLMMessage,
        LLMProvider,
        STTProvider,
        STTResult,
        TTSProvider,
    )
    from app.domains.assessment.service import AssessmentService
    from app.domains.assessment.triage import TriageService
    from app.domains.chat.service import ChatContext, ChatService
    from app.schemas.assessment import AssessmentResponse


class ChatServiceAdapter(ChatPort):
    """Adapter that wraps ChatService to implement ChatPort interface."""

    def __init__(self, chat_service: "ChatService"):
        self._chat_service = chat_service

    async def get_context(self, _user_id: str, session_id: str | None = None) -> "ChatContext":
        """Get chat context for a session by delegating to ChatService's ContextBuildStage."""
        if session_id is None:
            raise ValueError("ChatServiceAdapter.get_context requires session_id")

        session_uuid = UUID(session_id) if isinstance(session_id, str) else session_id

        # Import locally to avoid cycles
        from app.domains.chat.service import ContextBuildStage

        context = await ContextBuildStage(self._chat_service).run(
            session_id=session_uuid,
            skills_context=None,
            platform=None,
            precomputed_assessment=None,
            pipeline_run_id=None,
            request_id=None,
            user_id=None,
            org_id=None,
        )
        return context

    async def enrich_context(self, context: "ChatContext", _sources: list[str] = None) -> "ChatContext":
        """Currently a no-op; enrichment is handled inside ChatService pipeline."""
        return context

    async def store_message(self, message: "LLMMessage", session_id: str) -> str:
        """Persist a message into chat history via ChatService helper and return its ID."""
        session_uuid = UUID(session_id) if isinstance(session_id, str) else session_id

        # Generate a message id deterministically is out of scope; use uuid4
        from uuid import uuid4
        message_id = uuid4()

        # Import locally to avoid cycles
        await self._chat_service._save_interaction(
            session_id=session_uuid,
            role=message.role,
            content=message.content,
            message_id=message_id,
        )
        return str(message_id)

    async def prefetch_enrichers(self, session_id: str) -> dict[str, Any]:
        """Prefetch enricher data for a session by delegating to ChatService."""
        session_uuid = UUID(session_id) if isinstance(session_id, str) else session_id
        result = await self._chat_service.prefetch_enrichers(session_uuid)
        return {
            "is_onboarding": result.is_onboarding,
            "meta_summary_text": result.meta_summary_text,
            "summary": result.summary,
            "profile_text": result.profile_text,
            "last_n": result.last_n,
        }

    async def build_context(
        self,
        session_id: str,
        skills_context: list[Any] | None = None,
        platform: str | None = None,
        prefetched: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build chat context with all enrichments applied."""
        session_uuid = UUID(session_id) if isinstance(session_id, str) else session_id

        # Convert prefetched dict back to PrefetchedEnrichers if provided
        prefetched_enrichers = None
        if prefetched is not None:
            from app.domains.chat.service import PrefetchedEnrichers as PE
            prefetched_enrichers = PE(
                is_onboarding=prefetched.get("is_onboarding"),
                meta_summary_text=prefetched.get("meta_summary_text"),
                summary=prefetched.get("summary"),
                profile_text=prefetched.get("profile_text"),
                last_n=prefetched.get("last_n", []),
            )

        context = await self._chat_service.build_context(
            session_id=session_uuid,
            skills_context=skills_context,
            platform=platform,
            prefetched=prefetched_enrichers,
        )

        # Return context data as dict
        return {
            "messages": context.messages if hasattr(context, "messages") else [],
            "skills_context": getattr(context, "skills_context", None) or [],
        }


class LlmProviderAdapter(LlmPort):
    """Adapter that wraps LLMProvider to implement LlmPort interface."""

    def __init__(self, llm_provider: "LLMProvider"):
        self._llm_provider = llm_provider

    async def stream_completion(self, request: LlmRequest) -> AsyncIterator[str]:
        """Stream LLM completion token by token."""
        # Convert port request to provider format
        messages = request.messages  # Already LLMMessage format

        async for token in self._llm_provider.stream(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        ):
            yield token

    async def complete(self, request: LlmRequest) -> LlmResponse:
        """Get complete LLM response in one call."""
        # Convert port request to provider format
        messages = request.messages  # Already LLMMessage format

        response = await self._llm_provider.generate(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        return LlmResponse(
            content=response.content,
            model=response.model,
            usage={
                "tokens_in": response.tokens_in,
                "tokens_out": response.tokens_out,
                "total_tokens": response.tokens_in + response.tokens_out,
            },
        )


class SttProviderAdapter(SttPort):
    """Adapter that wraps STTProvider to implement SttPort interface."""

    def __init__(self, stt_provider: "STTProvider"):
        self._stt_provider = stt_provider

    async def transcribe(self, audio_data: bytes, model: str = None) -> "STTResult":
        """Transcribe audio to text."""
        return await self._stt_provider.transcribe(
            audio_data=audio_data,
            format=model or "wav",
            language="en",
        )


class TtsProviderAdapter(TtsPort):
    """Adapter that wraps TTSProvider to implement TtsPort interface."""

    def __init__(self, tts_provider: "TTSProvider"):
        self._tts_provider = tts_provider

    async def synthesize(self, text: str, voice: str = None, _model: str = None) -> AsyncIterator[bytes]:
        """Stream synthesized audio bytes using the provider's stream."""
        async for chunk in self._tts_provider.stream(
            text=text,
            voice=voice,
            format="mp3",
        ):
            yield chunk


class PolicyGatewayAdapter(PolicyPort):
    """Adapter that wraps PolicyGateway to implement PolicyPort interface."""

    def __init__(self, policy_gateway):
        self._policy_gateway = policy_gateway

    async def evaluate_message(self, _message: str, context: dict[str, Any]) -> dict[str, Any]:
        """Evaluate message against policies using PolicyGateway."""
        # Import lazily to avoid cycles
        from app.ai.substrate.policy.gateway import PolicyCheckpoint, PolicyContext

        policy_ctx = PolicyContext(
            pipeline_run_id=context.get("pipeline_run_id"),
            request_id=context.get("request_id"),
            session_id=context.get("session_id"),
            user_id=context.get("user_id"),
            org_id=context.get("org_id"),
            service=context.get("service", "chat"),
            trigger=context.get("trigger"),
            behavior=context.get("behavior"),
            quality_mode=context.get("quality_mode"),
            intent=context.get("intent", "chat"),
            prompt_tokens_estimate=context.get("prompt_tokens_estimate"),
        )

        decision = await self._policy_gateway.evaluate(
            checkpoint=PolicyCheckpoint.PRE_LLM,
            context=policy_ctx,
        )
        return {"decision": decision.decision, "reason": decision.reason}

    async def check_guardrails(self, content: str, context: dict[str, Any]) -> tuple[bool, str | None]:
        """Check content against guardrails using GuardrailsStage."""
        from app.ai.substrate.policy.guardrails import (
            GuardrailsCheckpoint,
            GuardrailsContext,
            GuardrailsDecision,
            GuardrailsStage,
        )

        guardrails_ctx = GuardrailsContext(
            pipeline_run_id=context.get("pipeline_run_id"),
            request_id=context.get("request_id"),
            session_id=context.get("session_id"),
            user_id=context.get("user_id"),
            org_id=context.get("org_id"),
            service=context.get("service", "chat"),
            intent=context.get("intent", "chat"),
            input_excerpt=content[:5000] if content else None,
        )
        result = await GuardrailsStage().evaluate(
            checkpoint=GuardrailsCheckpoint.PRE_LLM,
            context=guardrails_ctx,
        )
        return (result.decision == GuardrailsDecision.ALLOW, result.reason)


class AssessmentServiceAdapter(AssessmentPort):
    """Adapter that wraps AssessmentService to implement AssessmentPort interface."""

    def __init__(self, assessment_service: "AssessmentService"):
        self._assessment_service = assessment_service

    async def assess_response(self, user_message: str, _assistant_response: str, context: dict[str, Any]) -> "AssessmentResponse":
        """Assess chat response quality using underlying service."""
        from uuid import UUID as _UUID

        user_id = context.get("user_id")
        session_id = context.get("session_id")
        interaction_id = context.get("interaction_id")
        triage_decision = context.get("triage_decision")
        skill_ids = context.get("skill_ids", [])
        request_id = context.get("request_id")
        pipeline_run_id = context.get("pipeline_run_id")

        # Coerce to UUID where possible
        def _to_uuid(v):
            try:
                return _UUID(v) if isinstance(v, str) else v
            except Exception:
                return v

        return await self._assessment_service.assess_response(
            user_id=_to_uuid(user_id),
            session_id=_to_uuid(session_id),
            interaction_id=_to_uuid(interaction_id),
            user_response=user_message,
            skill_ids=[_to_uuid(s) for s in skill_ids],
            triage_decision=triage_decision,
            request_id=_to_uuid(request_id),
            pipeline_run_id=_to_uuid(pipeline_run_id),
        )

    async def get_assessment_history(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Not implemented: history retrieval is not exposed by AssessmentService yet."""
        raise NotImplementedError("Assessment history retrieval is not implemented")


class TriageServiceAdapter(TriagePort):
    """Adapter that wraps TriageService to implement TriagePort interface."""

    def __init__(self, triage_service: "TriageService"):
        self._triage_service = triage_service

    async def categorize_message(self, message: str, context: dict[str, Any]) -> str:
        """Delegates to triage service classification when available; returns a category string."""
        # Import lazily to avoid heavy dependencies
        try:
            from app.schemas.assessment import ChatMessage, ChatRole, TriageRequest
        except Exception:
            # Fallback: no-op categorization
            return "general"

        session_id = context.get("session_id")
        chat_context = context.get("context", [])

        # Coerce session id if needed
        try:
            s_uuid = UUID(session_id) if isinstance(session_id, str) else session_id
        except Exception:
            s_uuid = session_id

        # Build minimal triage request
        req = TriageRequest(
            session_id=s_uuid,
            user_response=message,
            context=[ChatMessage(role=(ChatRole.USER if m.get("role") == "user" else ChatRole.ASSISTANT), content=m.get("content", "")) for m in chat_context][-5:],
        )

        try:
            result = await self._triage_service.classify_response(request=req, interaction_id=context.get("interaction_id"))
            return getattr(result, "category", "general")
        except Exception:
            return "general"

    async def extract_entities(self, _message: str) -> dict[str, Any]:
        """Entity extraction is not standardized; return empty mapping."""
        return {}


class GuardrailsPortAdapter(GuardrailsPort):
    """Adapter that wraps GuardrailsStage to implement GuardrailsPort interface."""

    def __init__(self, guardrails_stage):
        self._guardrails_stage = guardrails_stage

    async def check_content(self, content: str, context: dict[str, Any]) -> tuple[bool, str | None]:
        """Check content against guardrails using GuardrailsStage."""
        from app.ai.substrate.policy.guardrails import (
            GuardrailsCheckpoint,
            GuardrailsContext,
            GuardrailsDecision,
        )

        guardrails_ctx = GuardrailsContext(
            pipeline_run_id=context.get("pipeline_run_id"),
            request_id=context.get("request_id"),
            session_id=context.get("session_id"),
            user_id=context.get("user_id"),
            org_id=context.get("org_id"),
            service=context.get("service", "chat"),
            intent=context.get("intent", "chat"),
            input_excerpt=content[:5000] if content else None,
        )
        result = await self._guardrails_stage.evaluate(
            checkpoint=GuardrailsCheckpoint.PRE_LLM,
            context=guardrails_ctx,
        )
        return (result.decision == GuardrailsDecision.ALLOW, result.reason)
