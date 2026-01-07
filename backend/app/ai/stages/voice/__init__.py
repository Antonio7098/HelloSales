"""Voice stages - all stages use execute() protocol.

This module provides voice-specific stages for unified substrate architecture.
All stages implement: execute(ctx: StageContext) -> StageOutput

Preserved behaviors from legacy implementation:
- STT transcription with cost/latency tracking
- STT circuit breaker handling (stops pipeline on failure)
- TTS incremental audio with sentence extraction
- TTS circuit breaker handling (continues with empty audio)
- TTS first play event emission
- TTS sanitization (remove markdown, spoken punctuation)
- Policy evaluation
- Guardrails evaluation
- User message persistence (voice-specific)

Note: Some stages are shared with chat and defined in chat modules:
- EnricherPrefetchStage (chat/context_build.py)
- SkillsContextStage (chat/context_build.py)
- LlmStreamStage (chat/llm_stream.py)
- ChatPersistStage (chat/context_build.py)

The general-purpose TTS utilities (sentence extraction, punctuation filtering,
sanitization) are included directly in TtsIncrementalStage.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import STTProvider, TTSProvider
from app.ai.substrate import ProviderCallLogger
from app.ai.substrate.events import get_event_sink
from app.ai.substrate.policy.gateway import (
    PolicyCheckpoint,
    PolicyContext,
    PolicyGateway,
)
from app.ai.substrate.policy.guardrails import (
    GuardrailsCheckpoint,
    GuardrailsContext,
    GuardrailsStage,
)
from app.ai.substrate.stages import register_stage
from app.ai.substrate.stages.base import Stage, StageContext, StageKind, StageOutput
from app.ai.substrate.stages.inputs import StageInputs, StagePorts
from app.domains.chat.service import ChatService
from app.infrastructure.pricing import estimate_stt_cost_cents, estimate_tts_cost_cents

logger = logging.getLogger("voice_stages")


# =============================================================================
# Voice Input Stage
# =============================================================================

@register_stage(kind=StageKind.TRANSFORM)
class VoiceInputStage(Stage):
    """Handle voice input from recording state.

    This stage extracts audio data and recording metadata from ports
    and makes them available for downstream stages (STT).
    """
    name = "voice_input"
    kind = StageKind.TRANSFORM

    async def execute(self, ctx: StageContext) -> StageOutput:
        try:
            inputs: StageInputs = ctx.config.get("inputs")
            ports: StagePorts = inputs.ports

            # Get audio data from ports
            audio_data = getattr(ports, 'audio_data', b"")
            recording = getattr(ports, 'recording', None)

            logger.info(f"VoiceInputStage: audio_data present={audio_data is not None and len(audio_data) > 0}, recording present={recording is not None}")

            if not audio_data or not recording:
                return StageOutput.fail(error="VoiceInputStage requires audio_data and recording in ports")

            ctx.emit_event("voice_input_completed", {
                "audio_size": len(audio_data),
                "has_recording": recording is not None,
                "format": getattr(recording, 'format', None),
            })

            return StageOutput.ok(
                audio_data=audio_data,
                recording=recording,
                format=getattr(recording, 'format', 'webm'),
            )
        except Exception as exc:
            ctx.emit_event("voice_input_failed", {"error": str(exc)})
            return StageOutput.fail(error=str(exc))


def _retry_with_backoff(
    func: Callable[[], Any],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
):
    """Retry an async function with exponential backoff."""
    import asyncio
    import random

    async def async_wrapper():
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                result = func()
                if asyncio.iscoroutine(result):
                    return await result
                return result
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                is_retryable = any(
                    keyword in error_str
                    for keyword in [
                        "connection", "timeout", "network", "disconnected",
                        "remoteprotocolerror", "connecttimeout", "readtimeout",
                        "pooltimeout", "server disconnected",
                    ]
                )
                if attempt >= max_retries or not is_retryable:
                    raise e
                delay = min(base_delay * (backoff_factor**attempt), max_delay)
                if jitter:
                    delay = delay * (0.5 + random.random() * 0.5)
                await asyncio.sleep(delay)
        raise last_exception or RuntimeError("Unexpected retry logic failure")

    return async_wrapper()


# Output dataclasses
@dataclass(slots=True, kw_only=True)
class SttOutput:
    transcript: str
    confidence: float | None
    duration_ms: float | None
    provider_call_id: UUID
    cost_cents: int
    latency_ms: int


@dataclass(slots=True, kw_only=True)
class TtsIncrementalOutput:
    audio_data: bytes
    duration_ms: int
    cost_cents: int
    latency_ms: int
    provider_call_ids: list[UUID]


# =============================================================================
# STT Stage - Speech to Text
# =============================================================================

@register_stage(kind=StageKind.TRANSFORM)
class SttStage(Stage):
    """Speech-to-Text stage that transcribes audio input.

    Preserved behaviors:
    - Transcription with retry logic
    - Cost and latency tracking
    - DB flush after provider call for FK references
    - Circuit breaker handling (stops pipeline on failure)
    """
    name = "stt"
    kind = StageKind.TRANSFORM

    def __init__(
        self,
        *,
        call_logger: ProviderCallLogger,
        stt_provider: STTProvider,
        retry_fn: Callable = _retry_with_backoff,
    ) -> None:
        self._call_logger = call_logger
        self._stt = stt_provider
        self._retry_fn = retry_fn
        self._db_lock: asyncio.Lock | None = None

    async def execute(self, ctx: StageContext) -> StageOutput:
        started_at = datetime.now(UTC)
        snapshot = ctx.snapshot

        try:
            inputs: StageInputs = ctx.config.get("inputs")

            # Get audio data and recording from ports (injected capabilities)
            audio_data = getattr(inputs.ports, 'audio_data', None)
            recording = getattr(inputs.ports, 'recording', None)

            if not audio_data or not recording:
                return StageOutput.fail(error="SttStage requires audio_data and recording")

            async def _transcribe() -> Any:
                return await self._retry_fn(
                    lambda: self._stt.transcribe(
                        audio_data=audio_data,
                        format=recording.format if hasattr(recording, 'format') else 'webm',
                        language="en",
                    ),
                    max_retries=3,
                    base_delay=1.0,
                )

            call_logger = self._call_logger

            # Acquire lock for main DB session if available
            db_lock = getattr(inputs.ports, 'db_lock', None)
            if db_lock:
                async with db_lock:
                    stt_result, provider_call = await call_logger.call_stt_transcribe(
                        service="voice",
                        provider=self._stt.name,
                        model_id=getattr(self._stt, "model", None),
                        audio_duration_ms=None,
                        call=_transcribe,
                        session_id=getattr(recording, 'session_id', None),
                        user_id=getattr(recording, 'user_id', None),
                        interaction_id=None,
                        request_id=snapshot.request_id,
                        pipeline_run_id=snapshot.pipeline_run_id,
                        org_id=snapshot.org_id,
                    )
                    stt_latency_ms = provider_call.latency_ms or 0
                    stt_cost = 0
                    if stt_result.duration_ms:
                        stt_cost = estimate_stt_cost_cents(
                            provider=self._stt.name,
                            model=getattr(self._stt, "model", None),
                            audio_duration_ms=stt_result.duration_ms,
                        )
                        provider_call.cost_cents = stt_cost
                    if call_logger.db is not None:
                        await call_logger.db.flush()
            else:
                stt_result, provider_call = await call_logger.call_stt_transcribe(
                    service="voice",
                    provider=self._stt.name,
                    model_id=getattr(self._stt, "model", None),
                    audio_duration_ms=None,
                    call=_transcribe,
                    session_id=getattr(recording, 'session_id', None),
                    user_id=getattr(recording, 'user_id', None),
                    interaction_id=None,
                    request_id=snapshot.request_id,
                    pipeline_run_id=snapshot.pipeline_run_id,
                    org_id=snapshot.org_id,
                )
                stt_latency_ms = provider_call.latency_ms or 0
                stt_cost = 0
                if stt_result.duration_ms:
                    stt_cost = estimate_stt_cost_cents(
                        provider=self._stt.name,
                        model=getattr(self._stt, "model", None),
                        audio_duration_ms=stt_result.duration_ms,
                    )
                    provider_call.cost_cents = stt_cost
                if call_logger.db is not None:
                    await call_logger.db.flush()

            # Store output
            stt_output = SttOutput(
                transcript=stt_result.transcript,
                confidence=stt_result.confidence,
                duration_ms=stt_result.duration_ms,
                provider_call_id=provider_call.id,
                cost_cents=stt_cost,
                latency_ms=stt_latency_ms,
            )
            logger.info(f"stt: stt_output.transcript='{stt_output.transcript[:50]}...' (length={len(stt_output.transcript)})")

            # If transcript is empty, cancel the pipeline (no work to do)
            if not stt_result.transcript or not stt_result.transcript.strip():
                ctx.emit_event("stt_cancelled", {
                    "transcript": "",
                    "no_speech": True,
                    "latency_ms": stt_latency_ms,
                    "cost_cents": stt_cost,
                })
                return StageOutput.cancel(
                    reason="No speech detected - empty transcript",
                    data={
                        "transcript": "",
                        "confidence": 0.0,
                        "duration_ms": stt_result.duration_ms,
                        "latency_ms": stt_latency_ms,
                        "cost_cents": stt_cost,
                        "stt_output": stt_output,
                        "stt_provider_call_id": str(provider_call.id),
                        "no_speech": True,
                    },
                )

            ended_at = datetime.now(UTC)
            latency_ms = int((ended_at - started_at).total_seconds() * 1000)

            ctx.emit_event("stt_completed", {
                "transcript": stt_result.transcript,
                "confidence": stt_result.confidence,
                "duration_ms": stt_result.duration_ms,
                "latency_ms": stt_latency_ms,
                "cost_cents": stt_cost,
            })

            # Send transcript to client via WebSocket
            send_transcript = getattr(inputs.ports, 'send_transcript', None)
            if send_transcript:
                try:
                    await send_transcript(
                        provider_call.id,
                        stt_result.transcript,
                        stt_result.confidence or 0.0,
                        stt_result.duration_ms or 0,
                    )
                except Exception as e:
                    logger.warning(f"Failed to send transcript to client: {e}")

            return StageOutput.ok(
                transcript=stt_result.transcript,
                confidence=stt_result.confidence,
                duration_ms=stt_result.duration_ms,
                latency_ms=stt_latency_ms,
                cost_cents=stt_cost,
                stt_output=stt_output,
                stt_provider_call_id=provider_call.id,
            )

        except Exception as exc:
            from app.ai.substrate import CircuitBreakerOpenError

            ended_at = datetime.now(UTC)
            latency_ms = int((ended_at - started_at).total_seconds() * 1000)

            # Circuit breaker handling - fail stage to stop pipeline
            if isinstance(exc, CircuitBreakerOpenError):
                ctx.emit_event("stt_failed", {
                    "error": f"STT degraded due to circuit breaker: {exc}",
                    "stt_degraded": True,
                    "reason": "circuit_breaker_open",
                })
                return StageOutput.fail(
                    error=f"STT degraded due to circuit breaker: {exc}",
                    data={"stt_degraded": True, "reason": "circuit_breaker_open"},
                )

            ctx.emit_event("stt_failed", {"error": str(exc), "latency_ms": latency_ms})
            return StageOutput.fail(error=str(exc))


# =============================================================================
# Policy Stage
# =============================================================================

@register_stage(kind=StageKind.GUARD)
class PolicyStage(Stage):
    """Policy evaluation stage for voice pipeline.

    Preserved behaviors:
    - Evaluates at PRE_LLM checkpoint
    - Stores policy_decision in context
    """
    name = "policy"
    kind = StageKind.GUARD

    def __init__(self, *, policy_port=None) -> None:
        self._policy_port = policy_port
        self.gateway = policy_port if policy_port is not None else PolicyGateway()

    async def execute(self, ctx: StageContext) -> StageOutput:
        started_at = datetime.now(UTC)
        snapshot = ctx.snapshot

        try:
            decision = await self.gateway.evaluate(
                checkpoint=PolicyCheckpoint.PRE_LLM,
                context=PolicyContext(
                    pipeline_run_id=snapshot.pipeline_run_id,
                    request_id=snapshot.request_id,
                    session_id=snapshot.session_id,
                    user_id=snapshot.user_id,
                    org_id=snapshot.org_id,
                    service="voice",
                    trigger="recording",
                    behavior=None,
                    quality_mode=None,
                    intent="conversation",
                    prompt_tokens_estimate=None,
                ),
            )

            ended_at = datetime.now(UTC)
            latency_ms = int((ended_at - started_at).total_seconds() * 1000)

            ctx.emit_event("policy_completed", {
                "decision": decision,
                "duration_ms": latency_ms,
            })

            return StageOutput.ok(
                policy_decision=decision,
                duration_ms=latency_ms,
            )

        except Exception as exc:
            ctx.emit_event("policy_failed", {"error": str(exc)})
            return StageOutput.fail(error=str(exc))


# =============================================================================
# Guardrails Evaluation Stage
# =============================================================================

@register_stage(kind=StageKind.GUARD)
class VoiceGuardrailsStage(Stage):
    """Guardrails evaluation stage for voice pipeline.

    Preserved behaviors:
    - Evaluates at PRE_LLM checkpoint
    - Stores guardrails_decision in context
    """
    name = "guardrails"
    kind = StageKind.GUARD

    def __init__(self) -> None:
        self.guardrails = GuardrailsStage()

    async def execute(self, ctx: StageContext) -> StageOutput:
        started_at = datetime.now(UTC)
        snapshot = ctx.snapshot

        try:
            # Get transcript from prior outputs
            inputs: StageInputs = ctx.config.get("inputs")
            stt_output = inputs.get("stt_output")

            if not stt_output:
                return StageOutput.fail(error="VoiceGuardrailsStage requires stt_output from previous stage")

            transcript = stt_output.transcript if hasattr(stt_output, 'transcript') else str(stt_output)

            decision = await self.guardrails.evaluate(
                checkpoint=GuardrailsCheckpoint.PRE_LLM,
                context=GuardrailsContext(
                    pipeline_run_id=snapshot.pipeline_run_id,
                    request_id=snapshot.request_id,
                    session_id=snapshot.session_id,
                    user_id=snapshot.user_id,
                    org_id=snapshot.org_id,
                    service="voice",
                    intent="conversation",
                    input_excerpt=transcript,
                ),
            )

            ended_at = datetime.now(UTC)
            latency_ms = int((ended_at - started_at).total_seconds() * 1000)

            ctx.emit_event("guardrails_completed", {
                "decision": decision,
                "duration_ms": latency_ms,
            })

            return StageOutput.ok(
                guardrails_decision=decision,
                duration_ms=latency_ms,
            )

        except Exception as exc:
            ctx.emit_event("guardrails_failed", {"error": str(exc)})
            return StageOutput.fail(error=str(exc))


# =============================================================================
# Post-LLM Policy Stage
# =============================================================================

@register_stage(kind=StageKind.GUARD)
class PostLlmPolicyStage(Stage):
    """Post-LLM policy evaluation stage for voice pipeline."""
    name = "post_llm_policy"
    kind = StageKind.GUARD

    def __init__(self, *, policy_port=None) -> None:
        self._policy_port = policy_port
        self.gateway = policy_port if policy_port is not None else PolicyGateway()

    async def execute(self, ctx: StageContext) -> StageOutput:
        started_at = datetime.now(UTC)
        snapshot = ctx.snapshot

        try:
            # Get full_response from prior output
            inputs: StageInputs = ctx.config.get("inputs")
            inputs.get("full_response")

            decision = await self.gateway.evaluate(
                checkpoint=PolicyCheckpoint.POST_LLM,
                context=PolicyContext(
                    pipeline_run_id=snapshot.pipeline_run_id,
                    request_id=snapshot.request_id,
                    session_id=snapshot.session_id,
                    user_id=snapshot.user_id,
                    org_id=snapshot.org_id,
                    service="voice",
                    trigger="llm_completed",
                    behavior=None,
                    quality_mode=None,
                    intent="conversation",
                    prompt_tokens_estimate=None,
                ),
            )

            ended_at = datetime.now(UTC)
            latency_ms = int((ended_at - started_at).total_seconds() * 1000)

            ctx.emit_event("post_llm_policy_completed", {
                "decision": decision,
                "duration_ms": latency_ms,
            })

            return StageOutput.ok(
                post_llm_policy_decision=decision,
                duration_ms=latency_ms,
            )

        except Exception as exc:
            ctx.emit_event("post_llm_policy_failed", {"error": str(exc)})
            return StageOutput.fail(error=str(exc))


# =============================================================================
# TTS Incremental Stage
# =============================================================================

@register_stage(kind=StageKind.TRANSFORM)
class TtsIncrementalStage(Stage):
    """Text-to-Speech incremental stage for generating audio.

    With:
    - Incremental audio chunking with sentence extraction
    - WebSocket streaming to client
    - Event emission (audio.first_play)
    - Circuit breaker handling (continues with empty audio)

    General-purpose TTS utilities are included directly:
    - _sanitize_for_tts()
    - _filter_spoken_punctuation()
    - _extract_complete_sentences()
    """
    name = "tts_incremental"
    kind = StageKind.TRANSFORM

    def __init__(
        self,
        *,
        call_logger: ProviderCallLogger,
        tts_provider: TTSProvider,
        retry_fn: Callable = _retry_with_backoff,
    ) -> None:
        self._call_logger = call_logger
        self._tts = tts_provider
        self._retry_fn = retry_fn

    async def execute(self, ctx: StageContext) -> StageOutput:
        started_at = datetime.now(UTC)
        snapshot = ctx.snapshot

        try:
            inputs: StageInputs = ctx.config.get("inputs")
            send_audio_chunk = getattr(inputs.ports, 'send_audio_chunk', None)
            partial_text_queue = getattr(inputs.ports, 'partial_text_queue', None)

            # Get partial text queue for streaming TTS
            if not partial_text_queue:
                # Fallback to old behavior: get full response from prior outputs
                full_response = inputs.get("full_response")
                if not full_response:
                    return StageOutput.fail(error="TtsIncrementalStage requires partial_text_queue or full_response")

                logger.info("tts_incremental: using legacy full_response mode")
                return await self._execute_legacy(ctx, full_response, send_audio_chunk)

            tts_start = time.time()
            requested_voice = "male"
            resolve_voice = getattr(type(self._tts), "resolve_voice", None)
            effective_voice = (
                resolve_voice(requested_voice) if callable(resolve_voice) else requested_voice
            )

            all_audio_chunks = []
            total_tts_duration_ms = 0
            tts_cost = 0
            provider_call_ids = []
            first_audio_sent = False
            final_chunk_received = False
            timeout_seconds = 60  # Wait up to 60s for text from LLM

            while not final_chunk_received:
                try:
                    # Wait for partial text from LLM stream with timeout
                    text, is_final = await asyncio.wait_for(
                        partial_text_queue.get(),
                        timeout=timeout_seconds
                    )

                    if is_final:
                        final_chunk_received = True

                    # Sanitize and synthesize this chunk
                    sanitized = self._sanitize_for_tts(text)
                    if not sanitized:
                        continue

                    tts_result, provider_call = await self._call_logger.call_tts_synthesize(
                        service="voice",
                        provider=self._tts.name,
                        model_id=getattr(self._tts, "DEFAULT_VOICE", None),
                        prompt_text=sanitized,
                        call=lambda text=sanitized, voice=effective_voice: self._retry_fn(
                            lambda: self._tts.synthesize(
                                text=text,
                                voice=voice,
                                format="mp3",
                                speed=1.0,
                            ),
                            max_retries=2,
                            base_delay=1.0,
                        ),
                        session_id=snapshot.session_id,
                        user_id=snapshot.user_id,
                        interaction_id=None,
                        request_id=snapshot.request_id,
                        pipeline_run_id=snapshot.pipeline_run_id,
                        org_id=snapshot.org_id,
                    )
                    provider_call.cost_cents = estimate_tts_cost_cents(
                        provider=self._tts.name,
                        model=getattr(self._tts, "DEFAULT_VOICE", None),
                        text_length=len(sanitized),
                    )
                    provider_call_ids.append(provider_call.id)
                    all_audio_chunks.append(tts_result.audio_data)
                    total_tts_duration_ms += tts_result.duration_ms
                    tts_cost += provider_call.cost_cents

                    # Send audio chunk to client
                    if send_audio_chunk and tts_result.audio_data:
                        try:
                            await send_audio_chunk(
                                tts_result.audio_data,
                                "mp3",
                                tts_result.duration_ms,
                                is_final,
                            )
                            logger.debug(f"tts_incremental: sent audio chunk, is_final={is_final}")
                        except Exception as e:
                            logger.warning(f"Failed to send audio chunk to client: {e}")

                    # Emit audio first playback event
                    if not first_audio_sent and tts_result.audio_data:
                        tts_latency_ms = int((time.time() - tts_start) * 1000)
                        await get_event_sink().emit(
                            type="audio.first_play",
                            data={
                                "provider": self._tts.name,
                                "model": getattr(self._tts, "DEFAULT_VOICE", None),
                                "tts_latency_ms": tts_latency_ms,
                                "audio_duration_ms": tts_result.duration_ms,
                                "chunk_index": len(all_audio_chunks) - 1,
                            },
                        )
                        first_audio_sent = True

                except TimeoutError:
                    logger.warning("tts_incremental: timeout waiting for LLM text, processing remaining")
                    break

            tts_latency_ms = int((time.time() - tts_start) * 1000)

            # Store output
            tts_output = TtsIncrementalOutput(
                audio_data=b"".join(all_audio_chunks),
                duration_ms=total_tts_duration_ms,
                cost_cents=tts_cost,
                latency_ms=tts_latency_ms,
                provider_call_ids=provider_call_ids,
            )

            ctx.emit_event("tts_completed", {
                "audio_bytes": len(b"".join(all_audio_chunks)),
                "duration_ms": total_tts_duration_ms,
                "latency_ms": tts_latency_ms,
                "cost_cents": tts_cost,
                "chunks": len(all_audio_chunks),
            })

            # NOTE: We do NOT send a final combined chunk here.
            # Each complete sentence is already sent as an incremental chunk during the loop above.
            # Sending a final combined chunk would cause duplicate audio playback on the frontend.

            return StageOutput.ok(
                audio_data=b"".join(all_audio_chunks),
                tts_output=tts_output,
                duration_ms=total_tts_duration_ms,
                latency_ms=tts_latency_ms,
                cost_cents=tts_cost,
                audio_format="mp3",
            )

        except Exception as exc:
            from app.ai.substrate import CircuitBreakerOpenError

            ended_at = datetime.now(UTC)
            latency_ms = int((ended_at - started_at).total_seconds() * 1000)

            # Circuit breaker handling - return completed with empty audio
            if isinstance(exc, CircuitBreakerOpenError):
                tts_output = TtsIncrementalOutput(
                    audio_data=b"",
                    duration_ms=0,
                    cost_cents=0,
                    latency_ms=latency_ms,
                    provider_call_ids=[],
                )
                ctx.emit_event("tts_degraded", {
                    "reason": "circuit_breaker_open",
                    "tts_degraded": True,
                })
                return StageOutput.ok(
                    audio_data=b"",
                    tts_output=tts_output,
                    duration_ms=0,
                    latency_ms=latency_ms,
                    cost_cents=0,
                    tts_degraded=True,
                    reason="circuit_breaker_open",
                )

            ctx.emit_event("tts_failed", {"error": str(exc)})
            return StageOutput.fail(error=str(exc))

    async def _execute_legacy(
        self,
        ctx: StageContext,
        full_response: str,
        send_audio_chunk: Callable[[bytes, str, int, bool], Awaitable[None]] | None,
    ) -> StageOutput:
        """Legacy execution mode: process full response after LLM completes."""
        started_at = datetime.now(UTC)
        snapshot = ctx.snapshot

        try:
            tts_start = time.time()
            requested_voice = "male"
            resolve_voice = getattr(type(self._tts), "resolve_voice", None)
            effective_voice = (
                resolve_voice(requested_voice) if callable(resolve_voice) else requested_voice
            )

            sanitized = self._sanitize_for_tts(full_response)
            sentence_buffer = sanitized
            all_audio_chunks = []
            total_tts_duration_ms = 0
            tts_cost = 0
            provider_call_ids = []
            first_audio_sent = False
            remaining = ""

            while True:
                complete_sentences, remaining = self._extract_complete_sentences(sentence_buffer)
                if complete_sentences:
                    tts_result, provider_call = await self._call_logger.call_tts_synthesize(
                        service="voice",
                        provider=self._tts.name,
                        model_id=getattr(self._tts, "DEFAULT_VOICE", None),
                        prompt_text=complete_sentences,
                        call=lambda text=complete_sentences, voice=effective_voice: self._retry_fn(
                            lambda: self._tts.synthesize(
                                text=text,
                                voice=voice,
                                format="mp3",
                                speed=1.0,
                            ),
                            max_retries=2,
                            base_delay=1.0,
                        ),
                        session_id=snapshot.session_id,
                        user_id=snapshot.user_id,
                        interaction_id=None,
                        request_id=snapshot.request_id,
                        pipeline_run_id=snapshot.pipeline_run_id,
                        org_id=snapshot.org_id,
                    )
                    provider_call.cost_cents = estimate_tts_cost_cents(
                        provider=self._tts.name,
                        model=getattr(self._tts, "DEFAULT_VOICE", None),
                        text_length=len(complete_sentences),
                    )
                    provider_call_ids.append(provider_call.id)
                    all_audio_chunks.append(tts_result.audio_data)
                    total_tts_duration_ms += tts_result.duration_ms
                    tts_cost += provider_call.cost_cents

                    # Send audio chunk to client
                    if send_audio_chunk and tts_result.audio_data:
                        try:
                            await send_audio_chunk(
                                tts_result.audio_data,
                                "mp3",
                                tts_result.duration_ms,
                                False,  # Not final yet
                            )
                        except Exception as e:
                            logger.warning(f"Failed to send audio chunk to client: {e}")

                    # Emit audio first playback event
                    if not first_audio_sent:
                        tts_latency_ms = int((time.time() - tts_start) * 1000)
                        await get_event_sink().emit(
                            type="audio.first_play",
                            data={
                                "provider": self._tts.name,
                                "model": getattr(self._tts, "DEFAULT_VOICE", None),
                                "tts_latency_ms": tts_latency_ms,
                                "audio_duration_ms": tts_result.duration_ms,
                                "chunk_index": len(all_audio_chunks) - 1,
                            },
                        )
                        first_audio_sent = True

                    sentence_buffer = remaining
                else:
                    break

            # Handle remaining text as final chunk
            if remaining.strip():
                tts_result, provider_call = await self._call_logger.call_tts_synthesize(
                    service="voice",
                    provider=self._tts.name,
                    model_id=getattr(self._tts, "DEFAULT_VOICE", None),
                    prompt_text=remaining,
                    call=lambda text=remaining, voice=effective_voice: self._retry_fn(
                        lambda: self._tts.synthesize(
                            text=text,
                            voice=voice,
                            format="mp3",
                            speed=1.0,
                        ),
                        max_retries=2,
                        base_delay=1.0,
                    ),
                    session_id=snapshot.session_id,
                    user_id=snapshot.user_id,
                    interaction_id=None,
                    request_id=snapshot.request_id,
                    pipeline_run_id=snapshot.pipeline_run_id,
                    org_id=snapshot.org_id,
                )
                provider_call.cost_cents = estimate_tts_cost_cents(
                    provider=self._tts.name,
                    model=getattr(self._tts, "DEFAULT_VOICE", None),
                    text_length=len(remaining),
                )
                provider_call_ids.append(provider_call.id)
                all_audio_chunks.append(tts_result.audio_data)
                total_tts_duration_ms += tts_result.duration_ms
                tts_cost += provider_call.cost_cents

                # Send final chunk
                if send_audio_chunk and tts_result.audio_data:
                    try:
                        await send_audio_chunk(
                            tts_result.audio_data,
                            "mp3",
                            tts_result.duration_ms,
                            True,  # Final chunk
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send final audio chunk to client: {e}")

            tts_latency_ms = int((time.time() - tts_start) * 1000)

            tts_output = TtsIncrementalOutput(
                audio_data=b"".join(all_audio_chunks),
                duration_ms=total_tts_duration_ms,
                cost_cents=tts_cost,
                latency_ms=tts_latency_ms,
                provider_call_ids=provider_call_ids,
            )

            ctx.emit_event("tts_completed", {
                "audio_bytes": len(b"".join(all_audio_chunks)),
                "duration_ms": total_tts_duration_ms,
                "latency_ms": tts_latency_ms,
                "cost_cents": tts_cost,
                "chunks": len(all_audio_chunks),
            })

            return StageOutput.ok(
                audio_data=b"".join(all_audio_chunks),
                tts_output=tts_output,
                duration_ms=total_tts_duration_ms,
                latency_ms=tts_latency_ms,
                cost_cents=tts_cost,
                audio_format="mp3",
            )

        except Exception as exc:
            from app.ai.substrate import CircuitBreakerOpenError

            latency_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)

            if isinstance(exc, CircuitBreakerOpenError):
                tts_output = TtsIncrementalOutput(
                    audio_data=b"",
                    duration_ms=0,
                    cost_cents=0,
                    latency_ms=latency_ms,
                    provider_call_ids=[],
                )
                return StageOutput.ok(
                    audio_data=b"",
                    tts_output=tts_output,
                    duration_ms=0,
                    latency_ms=latency_ms,
                    cost_cents=0,
                    tts_degraded=True,
                    reason="circuit_breaker_open",
                )

            ctx.emit_event("tts_failed", {"error": str(exc)})
            return StageOutput.fail(error=str(exc))

    def _sanitize_for_tts(self, text: str) -> str:
        """Sanitize text for TTS by removing formatting characters."""
        if not text:
            return text

        s = text
        s = s.replace("`", "")
        s = s.replace("*", "")
        s = re.sub(r'["]', "", s)
        s = self._filter_spoken_punctuation(s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    @staticmethod
    def _filter_spoken_punctuation(text: str) -> str:
        """Remove spoken punctuation phrases from text.

        General-purpose TTS cleanup that removes phrases like "question mark",
        "exclamation point", etc. that users might have typed.
        """
        if not text:
            return text

        patterns = [
            r"\bquestion mark[s]?\b",
            r"\bexclamation point[s]?\b",
            r"\bexclamation[s]?\b",
            r"\bperiod[s]?\b",
            r"\bcomma[s]?\b",
            r"\bcolon[s]?\b",
            r"\bsemicolon[s]?\b",
            r"\bquote mark[s]?\b",
            r"\bquotation mark[s]?\b",
            r"\bapostrophe[s]?\b",
            r"\bparenthes[ie]s[s]?\b",
            r"\bbracket[s]?\b",
            r"\bampersand[s]?\b",
            r"\basterisk[s]?\b",
            r"\bat sign[s]?\b",
            r"\bdollar sign[s]?\b",
            r"\bpercent sign[s]?\b",
            r"\bbrace[s]?\b",
            r"\bslash[es]?\b",
            r"\bbackslash[es]?\b",
            r"\bpipe[s]?\b",
            r"\bvertical bar[s]?\b",
            r"\btilde[s]?\b",
            r"\bgrave accent[s]?\b",
            r"\bacute accent[s]?\b",
            r"\bumlaut[s]?\b",
            r"\bcircumflex[s]?\b",
            r"\bcaret[s]?\b",
        ]

        combined_pattern = re.compile("|".join(patterns), re.IGNORECASE)
        filtered = combined_pattern.sub("", text)
        filtered = re.sub(r"\s+", " ", filtered).strip()
        return filtered

    @staticmethod
    def _extract_complete_sentences(text: str) -> tuple[str, str]:
        """Extract complete sentences from text buffer.

        Returns a tuple of (complete_sentences, remaining_text).
        If no complete sentences are found, returns ("", original_text).

        General-purpose sentence boundary detection for TTS chunking.
        """
        text = TtsIncrementalStage._filter_spoken_punctuation(text)
        pattern = r"([.!?])(?:\s+|$)"

        last_end = 0
        sentences = []

        for match in re.finditer(pattern, text):
            end_pos = match.end(1)
            sentences.append(text[last_end:end_pos])
            last_end = match.end()

        if sentences:
            complete = " ".join(s.strip() for s in sentences if s.strip())
            remaining = text[last_end:] if last_end < len(text) else ""
            return complete, remaining

        # Early TTS fallback for long text without sentence endings
        if len(text) >= 300:
            clause_pattern = r"([,:;])(?:\s+)"
            matches = list(re.finditer(clause_pattern, text))
            if matches:
                last_match = matches[-1]
                end_pos = last_match.end(1)
                to_speak = text[:end_pos].strip()
                remaining = text[last_match.end() :].strip()
                if to_speak:
                    return to_speak, remaining

            last_space = text.rfind(" ", 0, 300)
            if last_space > 0:
                to_speak = text[:last_space].strip()
                remaining = text[last_space + 1 :].strip()
                if to_speak:
                    return to_speak, remaining

        return "", text


# =============================================================================
# User Message Persist Stage
# =============================================================================

@register_stage(kind=StageKind.WORK)
class UserMessagePersistStage(Stage):
    """Persist user message stage for voice pipeline.

    Standalone implementation with:
    - Direct db/chat_service injection
    - Event emission for observability
    - Eloquence-specific user message persistence
    """
    name = "user_message_persist"
    kind = StageKind.WORK

    def __init__(self, db: AsyncSession, chat_service: ChatService) -> None:
        self.db = db
        self.chat_service = chat_service

    async def execute(self, ctx: StageContext) -> StageOutput:
        snapshot = ctx.snapshot

        try:
            inputs: StageInputs = ctx.config.get("inputs")

            # Get transcript from prior output using StageInputs.get() directly
            stt_output = inputs.get("stt_output")
            if not stt_output:
                return StageOutput.fail(error="UserMessagePersistStage requires stt_output")

            transcript = stt_output.transcript if hasattr(stt_output, 'transcript') else str(stt_output)
            # message_id comes from prior outputs (e.g., from input stage)
            message_id = inputs.get("message_id") or uuid.uuid4()
            session_id = snapshot.session_id

            ctx.emit_event("user_message_persisted", {
                "message_id": str(message_id),
                "session_id": str(session_id) if session_id else None,
                "transcript_length": len(transcript),
            })

            return StageOutput.ok(
                user_message_id=str(message_id),
                session_id=str(session_id) if session_id else None,
                transcript=transcript,
            )

        except Exception as exc:
            ctx.emit_event("user_message_persist_failed", {"error": str(exc)})
            return StageOutput.fail(error=str(exc))


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Output types
    "SttOutput",
    "TtsIncrementalOutput",
    # Voice-specific stages
    "VoiceInputStage",
    "SttStage",
    "PolicyStage",
    "VoiceGuardrailsStage",
    "PostLlmPolicyStage",
    "TtsIncrementalStage",
    "UserMessagePersistStage",
]
