"""VoicePipelineOrchestrator for SRP compliance.

Orchestrates the full STT → LLM → TTS voice pipeline.
"""

import asyncio
import inspect
import logging
import random
import re
import time
import uuid
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import STTProvider, TTSProvider
from app.ai.stages.chat.context_build import SkillsContextStage
from app.ai.stages.chat.llm_stream import StreamingLlmStage
from app.ai.stages.voice import (
    StreamingTtsStage,
    SttStage,
    UserMessagePersistStage,
    VoiceContextBuildStage,
)
from app.ai.substrate import PipelineRunLogger, ProviderCallLogger
from app.ai.substrate.events import get_event_sink
from app.ai.substrate.stages.base import SttOutput
from app.ai.substrate.stages.context import PipelineContext
from app.config import get_settings
from app.core.di import get_container
from app.domains.assessment.pipeline import backfill_interaction_id
from app.domains.chat.service import ChatService
from app.domains.chat.stages import ChatResponsePersistStage
from app.infrastructure.pricing import estimate_llm_cost_cents, estimate_tts_cost_cents

logger = logging.getLogger("voice")


T = TypeVar("T")


@dataclass
class VoicePipelineResult:
    """Result from the full voice pipeline."""

    # STT results
    transcript: str
    transcript_confidence: float
    audio_duration_ms: int

    # LLM results
    response_text: str
    llm_latency_ms: int

    # TTS results
    audio_data: bytes
    audio_format: str
    tts_duration_ms: int

    # Message IDs
    user_message_id: uuid.UUID
    assistant_message_id: uuid.UUID

    # Cost tracking (hundredths-of-cents)
    stt_cost: int
    llm_cost: int
    tts_cost: int

    @property
    def total_cost(self) -> int:
        """Total cost in hundredths-of-cents."""
        return self.stt_cost + self.llm_cost + self.tts_cost


async def _retry_with_backoff(
    func: Callable[[], Any],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
) -> T:
    """Retry an async function with exponential backoff on network-related failures."""
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            result = func()

            if isinstance(result, AsyncGenerator):
                return result  # type: ignore[return-value]

            if inspect.isawaitable(result):
                return await result

            return result
        except Exception as e:
            last_exception = e

            error_str = str(e).lower()
            is_retryable = any(
                keyword in error_str
                for keyword in [
                    "connection",
                    "timeout",
                    "network",
                    "disconnected",
                    "remoteprotocolerror",
                    "connecttimeout",
                    "readtimeout",
                    "pooltimeout",
                    "server disconnected",
                ]
            )

            if attempt >= max_retries or not is_retryable:
                raise e

            delay = min(base_delay * (backoff_factor**attempt), max_delay)
            if jitter:
                delay = delay * (0.5 + random.random() * 0.5)

            logger.warning(
                f"Retryable error on attempt {attempt + 1}/{max_retries + 1}, "
                f"retrying in {delay:.2f}s",
                extra={
                    "service": "voice",
                    "error": str(e),
                    "attempt": attempt + 1,
                    "max_retries": max_retries + 1,
                    "delay": delay,
                },
            )

            await asyncio.sleep(delay)

    raise last_exception or RuntimeError("Unexpected retry logic failure")


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


async def _safe_call(coro):
    """Safely call an async coroutine, logging any exceptions."""
    try:
        await coro
    except Exception as e:
        logger.warning(f"Async task failed: {e}", exc_info=True)


class VoicePipelineOrchestrator:
    """Service for orchestrating the voice pipeline.

    Responsibilities:
    - Process recordings through STT → LLM → TTS
    - Manage pipeline cancellation (barge-in)
    - Text sanitization for T Sentence extraction forTS
    - incremental TTS

    Note: This class requires a ChatService for LLM handling and database
    access for logging. These are typically injected via the VoiceService.
    """

    def __init__(
        self,
        db: AsyncSession,
        stt_provider: STTProvider,
        tts_provider: TTSProvider,
        chat_service: ChatService,
    ) -> None:
        """Initialize pipeline orchestrator.

        Args:
            db: Database session
            stt_provider: STT provider
            tts_provider: TTS provider
            chat_service: Chat service for LLM handling
        """
        self.db = db
        self.stt = stt_provider
        self.tts = tts_provider
        self.chat = chat_service
        self.call_logger = ProviderCallLogger(db)
        self.pipeline_logger = PipelineRunLogger(db)

        # Active pipeline contexts by user_id for cancellation
        self._active_pipelines: dict[uuid.UUID, PipelineContext] = {}

    def _ensure_db_components(self, db: AsyncSession) -> None:
        """Ensure database-dependent components are created with the given session."""
        if self.db != db or self.call_logger is None:
            self.db = db
            self.call_logger = ProviderCallLogger(db)
            self.pipeline_logger = PipelineRunLogger(db)

    @staticmethod
    def _filter_spoken_punctuation(text: str) -> str:
        """Filter out literal spoken punctuation names like 'quote mark' or 'asterisk'."""
        # Common spoken punctuation variations (case-insensitive, word boundaries)
        patterns = [
            r"\bquote mark[s]?\b",
            r"\bquotation mark[s]?\b",
            r"\basterisk[s]?\b",
            r"\bstar[s]?\b",
            r"\bperiod[s]?\b",
            r"\bfull stop[s]?\b",
            r"\bcomma[s]?\b",
            r"\bcolon[s]?\b",
            r"\bsemicolon[s]?\b",
            r"\bexclamation mark[s]?\b",
            r"\bexclamation point[s]?\b",
            r"\bquestion mark[s]?\b",
            r"\bhash[s]?\b",
            r"\bpound sign[s]?\b",
            r"\bnumber sign[s]?\b",
            r"\bat sign[s]?\b",
            r"\bampersand[s]?\b",
            r"\bpercent sign[s]?\b",
            r"\bdollar sign[s]?\b",
            r"\bbracket[s]?\b",
            r"\bparenthes[ie]s[s]?\b",
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
    def _sanitize_for_tts(text: str) -> str:
        """Sanitize text before TTS to avoid speaking formatting characters."""
        if not text:
            return text

        s = text
        # Remove markdown/code markers
        s = s.replace("`", "")
        s = s.replace("*", "")
        # Remove double quotes (keep apostrophes for contractions)
        s = re.sub(r"[\"“”]", "", s)
        # Remove any literal spoken punctuation phrases
        s = VoicePipelineOrchestrator._filter_spoken_punctuation(s)
        # Normalize whitespace
        s = re.sub(r"\s+", " ", s).strip()
        return s

    @staticmethod
    def _extract_complete_sentences(text: str) -> tuple[str, str]:
        """Extract complete sentences from text buffer.

        Returns (sentences_to_speak, remaining_buffer).
        A sentence is considered complete when it ends with . ! or ?
        followed by a space or end of string.
        """
        # Filter out literal spoken punctuation names before processing
        text = VoicePipelineOrchestrator._filter_spoken_punctuation(text)

        # Find all positions where a sentence ends (. ! ? followed by space or end)
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

        # Early TTS fallback
        if len(text) >= VoicePipelineOrchestrator.EARLY_TTS_CHAR_THRESHOLD:
            clause_pattern = r"([,:;])(?:\s+)"
            matches = list(re.finditer(clause_pattern, text))
            if matches:
                last_match = matches[-1]
                end_pos = last_match.end(1)
                to_speak = text[:end_pos].strip()
                remaining = text[last_match.end() :].strip()
                if to_speak:
                    return to_speak, remaining

            # Fallback: break on last whitespace before threshold
            last_space = text.rfind(" ", 0, VoicePipelineOrchestrator.EARLY_TTS_CHAR_THRESHOLD)
            if last_space > 0:
                to_speak = text[:last_space].strip()
                remaining = text[last_space + 1 :].strip()
                if to_speak:
                    return to_speak, remaining

        return "", text

    # Threshold for forcing TTS even without sentence-ending punctuation
    EARLY_TTS_CHAR_THRESHOLD = 80

    async def cancel_pipeline(self, user_id: uuid.UUID) -> bool:
        """Cancel the active pipeline for a user (barge-in support).

        Args:
            user_id: User ID

        Returns:
            True if pipeline was cancelled, False if none active
        """
        pipeline_ctx = self._active_pipelines.get(user_id)
        if not pipeline_ctx:
            return False

        pipeline_ctx.canceled = True

        logger.info(
            "Voice pipeline canceled (barge-in)",
            extra={
                "service": "voice",
                "user_id": str(user_id),
                "pipeline_run_id": str(pipeline_ctx.pipeline_run_id) if pipeline_ctx.pipeline_run_id else None,
                "session_id": str(pipeline_ctx.session_id) if pipeline_ctx.session_id else None,
            },
        )

        return True

    def get_active_pipeline(self, user_id: uuid.UUID) -> PipelineContext | None:
        """Get the active pipeline context for a user."""
        return self._active_pipelines.get(user_id)

    async def process_recording(
        self,
        user_id: uuid.UUID,
        audio_chunks: list[bytes],
        session_id: uuid.UUID,
        message_id: uuid.UUID | None = None,
        pipeline_run_id: uuid.UUID | None = None,
        request_id: uuid.UUID | None = None,
        org_id: uuid.UUID | None = None,
        quality_mode: str = "fast",
        send_status: Callable[[str, str, dict[str, Any] | None], Any] | None = None,
        send_token: Callable[[str], Any] | None = None,
        send_transcript: Callable[[uuid.UUID, str, float, int], Any] | None = None,
        send_audio_chunk: Callable[[bytes, str, int, bool], Any] | None = None,
        model_id: str | None = None,
        platform: str | None = None,
    ) -> VoicePipelineResult:
        """Process recorded audio through the full STT → LLM → TTS pipeline.

        Args:
            user_id: User ID
            audio_chunks: List of audio chunks from recording
            session_id: Session ID
            message_id: Client-generated message ID for deduplication
            pipeline_run_id: Pipeline run ID for observability
            request_id: Request ID for tracing
            org_id: Organization ID
            quality_mode: Quality mode (fast, accurate)
            send_status: Callback to send status updates
            send_token: Callback to send streamed LLM tokens
            send_transcript: Callback to send transcript immediately after STT
            send_audio_chunk: Callback to send TTS audio chunks
            model_id: Override LLM model ID
            platform: Client platform

        Returns:
            VoicePipelineResult with all pipeline outputs and metadata
        """
        from app.ai.substrate import get_circuit_breaker

        settings = get_settings()
        breaker = get_circuit_breaker()
        container = get_container()

        if message_id is None:
            message_id = uuid.uuid4()
        if pipeline_run_id is None:
            pipeline_run_id = uuid.uuid4()
        if request_id is None:
            request_id = uuid.uuid4()

        logger.info(
            "Processing voice recording",
            extra={
                "service": "voice",
                "pipeline_run_id": str(pipeline_run_id),
                "session_id": str(session_id),
                "user_id": str(user_id),
                "chunks": len(audio_chunks),
                "quality_mode": quality_mode,
            },
        )

        # Validate quality_mode and set model accordingly
        valid_modes = {"fast", "accurate"}
        if quality_mode not in valid_modes:
            logger.warning(
                f"Invalid quality_mode: {quality_mode}, defaulting to 'fast'",
                extra={
                    "service": "voice",
                    "invalid_mode": quality_mode,
                },
            )
            quality_mode = "fast"

        actual_model_id = model_id or (
            settings.voice_llm_model_accurate if quality_mode == "accurate" else settings.voice_llm_model
        )

        user_message_id = message_id
        assistant_message_id = uuid.uuid4()

        try:
            # STT Stage
            stt_stage = SttStage(
                stt_provider=self.stt,
                event_sink=get_event_sink(),
                breaker=breaker,
            )

            stt_output: SttOutput = await stt_stage.run(
                audio_chunks=audio_chunks,
                pipeline_run_id=pipeline_run_id,
                request_id=request_id,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                quality_mode=quality_mode,
            )

            if send_transcript:
                await _safe_call(
                    send_transcript(
                        user_message_id,
                        stt_output.transcript,
                        stt_output.confidence,
                        stt_output.audio_duration_ms,
                    )
                )

            # Skills Stage
            skills_stage = SkillsContextStage(skill_service=container.skill_service)
            skills_context = await skills_stage.run(
                user_id=user_id,
                skill_ids=None,
                session_id=session_id,
                pipeline_run_id=pipeline_run_id,
                request_id=request_id,
                org_id=org_id,
            )

            # Context Build Stage
            context_stage = VoiceContextBuildStage(chat_service=self.chat)
            chat_context = await context_stage.run(
                session_id=session_id,
                skills_context=skills_context,
                platform=platform,
                precomputed_assessment=None,
                pipeline_run_id=pipeline_run_id,
                request_id=request_id,
                user_id=user_id,
                org_id=org_id,
            )

            # LLM Streaming Stage
            llm_stage = StreamingLlmStage(
                llm_provider=self.chat.llm,
                call_logger=self.call_logger,
                breaker=breaker,
                event_sink=get_event_sink(),
            )

            llm_token_buffer: list[str] = []
            llm_token_count = 0
            llm_start_time = time.time()
            llm_provider_name: str = ""
            llm_model: str = ""
            llm_ttft_ms: int = 0

            async for token, ttft_ms, provider, model in llm_stage.run(
                messages=chat_context.messages,
                max_tokens=settings.policy_llm_max_tokens,
                model=actual_model_id,
                pipeline_run_id=pipeline_run_id,
                request_id=request_id,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
            ):
                llm_token_buffer.append(token)
                llm_token_count += 1

                if send_token:
                    await _safe_call(send_token(token))

                if not llm_provider_name:
                    llm_provider_name = provider
                    llm_model = model
                    llm_ttft_ms = ttft_ms or 0

                    if send_status:
                        await send_status(
                            "llm",
                            "first_token",
                            {
                                "provider": llm_provider_name,
                                "model": llm_model,
                                "ttft_ms": llm_ttft_ms,
                            },
                        )

            llm_latency_ms = int((time.time() - llm_start_time) * 1000)
            full_response = "".join(llm_token_buffer)

            if send_status:
                await send_status(
                    "llm",
                    "completed",
                    {
                        "provider": llm_provider_name,
                        "model": llm_model,
                        "ttft_ms": llm_ttft_ms,
                        "token_count": llm_token_count,
                        "duration_ms": llm_latency_ms,
                    },
                )

            # TTS Streaming Stage
            tts_stage = StreamingTtsStage(
                tts_provider=self.tts,
                call_logger=self.call_logger,
                breaker=breaker,
                event_sink=get_event_sink(),
            )

            audio_data = b""
            tts_provider_name = self.tts.name
            audio_format = getattr(self.tts, "default_format", "pcm")
            tts_duration_ms = 0

            text_buffer = full_response
            text_buffer += " "  # Add trailing space to trigger final TTS

            async for _sentence, audio_bytes, duration_ms in tts_stage.run(
                text_generator=self._streaming_tts_text(
                    text=text_buffer,
                    early_threshold=self.EARLY_TTS_CHAR_THRESHOLD,
                ),
                pipeline_run_id=pipeline_run_id,
                request_id=request_id,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
            ):
                if audio_bytes:
                    is_final = len(text_buffer.strip()) == 0
                    audio_data += audio_bytes
                    tts_duration_ms = duration_ms

                    if send_audio_chunk:
                        await _safe_call(
                            send_audio_chunk(
                                audio_bytes,
                                audio_format,
                                duration_ms,
                                is_final,
                            )
                        )

            if send_status:
                await send_status(
                    "tts",
                    "completed",
                    {
                        "provider": tts_provider_name,
                        "format": audio_format,
                        "duration_ms": tts_duration_ms,
                    },
                )

            # Cost estimation
            estimated_tokens_in = len("".join(m.content for m in chat_context.messages)) // 4
            estimated_tokens_out = llm_token_count

            stt_cost = estimate_tts_cost_cents(
                provider=tts_provider_name,
                duration_ms=stt_output.audio_duration_ms,
            )
            llm_cost = estimate_llm_cost_cents(
                provider=llm_provider_name,
                model=llm_model,
                tokens_in=estimated_tokens_in,
                tokens_out=estimated_tokens_out,
            )
            tts_cost = estimate_tts_cost_cents(
                provider=tts_provider_name,
                duration_ms=tts_duration_ms,
            )

            # Persist user message
            user_msg_stage = UserMessagePersistStage(db=self.db)
            await user_msg_stage.run(
                user_id=user_id,
                session_id=session_id,
                message_id=user_message_id,
                content=stt_output.transcript,
                audio_duration_ms=stt_output.audio_duration_ms,
                stt_confidence=stt_output.confidence,
                pipeline_run_id=pipeline_run_id,
                request_id=request_id,
                org_id=org_id,
            )

            # Persist assistant message
            assistant_msg_stage = ChatResponsePersistStage(db=self.db)
            await assistant_msg_stage.run(
                user_id=user_id,
                session_id=session_id,
                message_id=assistant_message_id,
                content=full_response,
                pipeline_run_id=pipeline_run_id,
                request_id=request_id,
                org_id=org_id,
                llm_provider=llm_provider_name,
                llm_model=llm_model,
                llm_token_count=llm_token_count,
                llm_latency_ms=llm_latency_ms,
                llm_ttft_ms=llm_ttft_ms,
                tts_provider=tts_provider_name,
                tts_duration_ms=tts_duration_ms,
                stt_duration_ms=stt_output.audio_duration_ms,
                stt_confidence=stt_output.confidence,
            )

            await backfill_interaction_id(
                db=self.db,
                provider_call_id=None,
                interaction_id=assistant_message_id,
            )

            logger.info(
                "Voice pipeline completed successfully",
                extra={
                    "service": "voice",
                    "pipeline_run_id": str(pipeline_run_id),
                    "user_id": str(user_id),
                    "session_id": str(session_id),
                    "transcript_length": len(stt_output.transcript),
                    "response_length": len(full_response),
                    "audio_duration_ms": tts_duration_ms,
                    "total_cost": stt_cost + llm_cost + tts_cost,
                },
            )

            return VoicePipelineResult(
                transcript=stt_output.transcript,
                transcript_confidence=stt_output.confidence,
                audio_duration_ms=stt_output.audio_duration_ms,
                response_text=full_response,
                llm_latency_ms=llm_latency_ms,
                audio_data=audio_data,
                audio_format=audio_format,
                tts_duration_ms=tts_duration_ms,
                user_message_id=user_message_id,
                assistant_message_id=assistant_message_id,
                stt_cost=stt_cost,
                llm_cost=llm_cost,
                tts_cost=tts_cost,
            )

        except Exception as e:
            logger.exception(
                "Voice pipeline failed",
                extra={
                    "service": "voice",
                    "pipeline_run_id": str(pipeline_run_id),
                    "user_id": str(user_id),
                    "session_id": str(session_id),
                    "error": str(e),
                },
            )
            raise

    async def _streaming_tts_text(
        self,
        text: str,
        early_threshold: int = 80,
    ) -> AsyncGenerator[tuple[str, bool], None]:
        """Generate text chunks for streaming TTS.

        Yields (text_chunk, is_final) tuples.
        """
        buffer = text

        while buffer:
            complete, remaining = self._extract_complete_sentences(buffer)

            if complete:
                yield complete, False
                buffer = remaining
                continue

            # Check if we should emit early
            if len(buffer) >= early_threshold:
                # Look for clause boundary
                clause_pattern = r"([,:;])(?:\s+)"
                matches = list(re.finditer(clause_pattern, buffer))
                if matches:
                    last_match = matches[-1]
                    to_speak = buffer[: last_match.end(1)].strip()
                    buffer = buffer[last_match.end() :].strip()
                    if to_speak:
                        yield to_speak, False
                        continue

                # Fallback to word boundary
                last_space = buffer.rfind(" ", 0, early_threshold)
                if last_space > 0:
                    to_speak = buffer[:last_space].strip()
                    buffer = buffer[last_space + 1 :].strip()
                    if to_speak:
                        yield to_speak, False
                        continue

            # Not enough for early TTS, wait for more
            break

        # Yield remaining as final
        if buffer.strip():
            yield buffer.strip(), True
