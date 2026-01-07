import asyncio
import contextlib
import logging
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from app.ai.providers.base import LLMMessage, LLMProvider, TTSProvider
from app.ai.substrate import ProviderCallLogger
from app.ai.substrate.events import get_event_sink
from app.ai.substrate.stages import register_stage
from app.ai.substrate.stages.base import Stage, StageContext, StageKind, StageOutput
from app.ai.substrate.stages.inputs import StageInputs
from app.models import ProviderCall

logger = logging.getLogger(__name__)

SendStatus = Callable[[str, str, dict[str, Any] | None], Awaitable[None]]
SendToken = Callable[[str], Awaitable[None]]

# Retry helper for TTS calls
async def _tts_retry_with_backoff(
    fn,
    max_retries: int = 2,
    base_delay: float = 1.0,
) -> Any:
    """Retry a function with exponential backoff for TTS calls."""
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            result = fn()
            if asyncio.iscoroutine(result):
                return await result
            return result
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"TTS call failed, retrying in {delay}s: {exc}")
                await asyncio.sleep(delay)
            else:
                raise last_exc
    raise last_exc


class LlmStreamFailure(Exception):
    def __init__(self, original: Exception, stream_token_count: int) -> None:
        super().__init__(str(original))
        self.original = original
        self.stream_token_count = stream_token_count


@dataclass
class LlmStreamResult:
    full_text: str
    stream_token_count: int
    provider: str
    model: str | None
    ttft_ms: int | None
    provider_call: ProviderCall


@register_stage(kind=StageKind.TRANSFORM)
class LlmStreamStage(Stage):
    """LLM streaming stage for generating responses.

    This stage implements the unified execute() protocol while wrapping
    the existing run() method for backward compatibility.
    """
    name = "llm_stream"
    kind = StageKind.TRANSFORM

    def __init__(
        self,
        *,
        llm_provider: LLMProvider | None = None,
        call_logger: ProviderCallLogger | None = None,
        send_status: SendStatus | None = None,
        send_token: SendToken | None = None,
        tts_provider: TTSProvider | None = None,
        send_audio_chunk: Callable[[bytes, str, int, bool], Awaitable[None]] | None = None,
    ) -> None:
        self._llm_provider = llm_provider
        self._call_logger = call_logger
        self._send_status = send_status
        self._send_token = send_token
        self._tts_provider = tts_provider
        self._send_audio_chunk = send_audio_chunk

    async def execute(self, ctx: StageContext) -> StageOutput:
        """Execute LLM streaming using unified StageContext protocol."""
        started_at = time.time()
        snapshot = ctx.snapshot

        try:
            inputs: StageInputs = ctx.config.get("inputs")

            # Use injected dependencies first, fall back to inputs.get() for prior outputs
            llm_provider = self._llm_provider or inputs.get("llm_provider")
            call_logger = self._call_logger or inputs.get("call_logger")
            # Callbacks come from ports (injected) - these are set up at pipeline start
            send_status = self._send_status or getattr(inputs.ports, 'send_status', None)
            send_token = self._send_token or getattr(inputs.ports, 'send_token', None)
            tts_provider = self._tts_provider or getattr(inputs.ports, 'tts_provider', None)
            send_audio_chunk = self._send_audio_chunk or getattr(inputs.ports, 'send_audio_chunk', None)
            partial_text_queue = getattr(inputs.ports, 'partial_text_queue', None)

            logger.info(f"llm_stream: send_token is {'set' if send_token else 'None'}, type={type(send_token).__name__ if send_token else 'None'}")
            logger.info(f"llm_stream: tts_provider is {'set' if tts_provider else 'None'}, send_audio_chunk is {'set' if send_audio_chunk else 'None'}")
            if send_token and hasattr(send_token, '_emits_llm_first_token'):
                logger.info("llm_stream: send_token has _emits_llm_first_token attribute (from orchestrator wrapper)")

            # These come from prior outputs
            messages = inputs.get("messages", [])
            logger.info(f"llm_stream: messages={len(messages)}, prior_outputs keys={list(inputs.prior_outputs.keys())}")
            model_id = inputs.get("model_id")
            max_tokens = inputs.get("max_tokens")
            prompt_payload = inputs.get("prompt_payload")

            if not llm_provider:
                return StageOutput.fail(error="LlmStreamStage requires llm_provider")
            if not call_logger:
                return StageOutput.fail(error="LlmStreamStage requires call_logger")
            if not messages:
                logger.info(f"llm_stream: no messages found. prior_outputs keys={list(inputs.prior_outputs.keys())}")
                return StageOutput.fail(error="LlmStreamStage requires messages")

            # Call the run method with all required parameters
            result = await self.run(
                call_logger=call_logger,
                service="chat",
                llm=llm_provider,
                messages=messages,
                model_id=model_id,
                max_tokens=max_tokens,
                prompt_payload=prompt_payload,
                session_id=snapshot.session_id,
                user_id=snapshot.user_id,
                _interaction_id=snapshot.interaction_id,
                request_id=snapshot.request_id,
                pipeline_run_id=snapshot.pipeline_run_id,
                org_id=snapshot.org_id,
                stage_started_at=started_at,
                send_status=send_status,
                send_token=send_token,
                tts_provider=tts_provider,
                send_audio_chunk=send_audio_chunk,
                partial_text_queue=partial_text_queue,
            )

            ctx.emit_event("llm_stream_completed", {
                "full_text": result.full_text,
                "tokens": result.stream_token_count,
                "ttft_ms": result.ttft_ms,
            })

            return StageOutput.ok(
                full_response=result.full_text,
                llm_result={
                    "full_text": result.full_text,
                    "stream_token_count": result.stream_token_count,
                    "provider": result.provider,
                    "model": result.model,
                    "ttft_ms": result.ttft_ms,
                },
                stream_token_count=result.stream_token_count,
                ttft_ms=result.ttft_ms,
                provider=result.provider,
                model=result.model,
                assistant_message_id=str(uuid4()),  # Generate ID for persistence
            )

        except LlmStreamFailure as exc:
            ctx.emit_event("llm_stream_failed", {"error": str(exc)})
            return StageOutput.fail(error=f"LLM stream failed: {exc.original}")
        except Exception as exc:
            ctx.emit_event("llm_stream_failed", {"error": str(exc)})
            return StageOutput.fail(error=str(exc))

    async def run(
        self,
        *,
        call_logger: ProviderCallLogger,
        service: str,
        llm: LLMProvider,
        messages: list[LLMMessage],
        model_id: str | None,
        max_tokens: int | None,
        prompt_payload: list[dict[str, Any]] | None,
        session_id: UUID | None,
        user_id: UUID | None,
        _interaction_id: UUID | None,
        request_id: UUID | None,
        pipeline_run_id: UUID | None,
        org_id: UUID | None,
        stage_started_at: float,
        send_status: SendStatus | None,
        send_token: SendToken | None,
        tts_provider: TTSProvider | None = None,
        send_audio_chunk: Callable[[bytes, str, int, bool], Awaitable[None]] | None = None,
        partial_text_queue: asyncio.Queue[tuple[str, bool]] | None = None,
    ) -> LlmStreamResult:
        full_text = ""
        stream_token_count = 0
        effective_model = llm.resolve_model(model_id)
        ttft_ms: int | None = None
        emits_first_token_already = bool(getattr(send_token, "_emits_llm_first_token", False))

        # TTS state for incremental playback
        tts_sent_position = 0
        tts_first_audio_sent = False
        effective_voice = None
        if tts_provider:
            resolve_voice = getattr(type(tts_provider), "resolve_voice", None)
            effective_voice = resolve_voice("male") if callable(resolve_voice) else "male"

        # Emit LLM started event
        get_event_sink().try_emit(
            type="llm.started",
            data={
                "provider": llm.name,
                "model": effective_model,
            },
        )

        # Send WebSocket started event
        if send_status:
            await send_status("llm", "started", {
                "provider": llm.name,
                "model": effective_model,
            })

        try:
            kwargs: dict[str, Any] = {}
            if isinstance(max_tokens, int) and max_tokens > 0:
                kwargs["max_tokens"] = max_tokens

            stream, call_row = await call_logger.call_llm_stream(
                service=service,
                provider=llm.name,
                model_id=effective_model,
                prompt_messages=prompt_payload,
                stream=lambda: llm.stream(messages, model=effective_model, **kwargs),
                session_id=session_id,
                user_id=user_id,
                interaction_id=None,  # Interaction doesn't exist yet, will be linked later
                request_id=request_id,
                pipeline_run_id=pipeline_run_id,
                org_id=org_id,
            )

            # Track position up to which we've sent partial text
            last_sent_position = 0

            async for token in stream:
                full_text += token
                stream_token_count += 1

                if stream_token_count == 1:
                    ttft_ms = int((time.time() - stage_started_at) * 1000)
                    logger.info(f"llm_stream: received first token, ttft_ms={ttft_ms}")
                    if not emits_first_token_already:
                        get_event_sink().try_emit(
                            type="llm.first_token",
                            data={
                                "provider": llm.name,
                                "model": effective_model,
                            },
                        )
                    if send_status:
                        await send_status("llm", "streaming", None)

                if send_token:
                    logger.debug(f"llm_stream: sending token {stream_token_count}: '{token[:20]}...'")
                    await send_token(token)
                else:
                    if stream_token_count <= 5:
                        logger.warning(f"llm_stream: send_token is None, token {stream_token_count} not sent")

                # Do inline TTS when partial text is detected (for voice pipelines)
                if tts_provider and send_audio_chunk:
                    # Check for sentence endings in the new text
                    new_text = full_text[tts_sent_position:]
                    sentence_end_pattern = re.compile(r'[.!?][\s]+')

                    for match in sentence_end_pattern.finditer(new_text):
                        sentence_end = match.end()
                        sentence = full_text[:tts_sent_position + sentence_end].strip()
                        if sentence and len(sentence) > 2:
                            # Sanitize and synthesize
                            sanitized = self._sanitize_for_tts(sentence)
                            if sanitized:
                                try:
                                    tts_result = await _tts_retry_with_backoff(
                                        lambda text=sanitized, voice=effective_voice: tts_provider.synthesize(
                                            text=text,
                                            voice=voice,
                                            format="mp3",
                                            speed=1.0,
                                        ),
                                        max_retries=2,
                                        base_delay=1.0,
                                    )
                                    if tts_result and tts_result.audio_data:
                                        await send_audio_chunk(
                                            tts_result.audio_data,
                                            "mp3",
                                            tts_result.duration_ms,
                                            False,  # Not final
                                        )
                                        # Emit first audio event
                                        if not tts_first_audio_sent:
                                            tts_latency_ms = int((time.time() - stage_started_at) * 1000)
                                            get_event_sink().try_emit(
                                                type="audio.first_play",
                                                data={
                                                    "provider": tts_provider.name,
                                                    "model": getattr(tts_provider, "DEFAULT_VOICE", None),
                                                    "tts_latency_ms": tts_latency_ms,
                                                    "audio_duration_ms": tts_result.duration_ms,
                                                },
                                            )
                                            tts_first_audio_sent = True
                                        logger.debug(f"llm_stream: sent inline TTS for sentence: '{sentence[:30]}...'")
                                except Exception as e:
                                    logger.warning(f"llm_stream: inline TTS failed: {e}")
                            tts_sent_position += sentence_end
                            break  # Only send one sentence at a time

                    # Also send on long text without sentence endings (reduce latency)
                    remaining_new = full_text[tts_sent_position:]
                    if len(remaining_new) > 80:
                        clause_pattern = re.compile(r'[,;:][\s]+')
                        for match in clause_pattern.finditer(remaining_new):
                            clause_end = match.end()
                            clause = full_text[:tts_sent_position + clause_end].strip()
                            if clause and len(clause) > 10:
                                sanitized = self._sanitize_for_tts(clause)
                                if sanitized:
                                    try:
                                        tts_result = await _tts_retry_with_backoff(
                                            lambda text=sanitized, voice=effective_voice: tts_provider.synthesize(
                                                text=text,
                                                voice=voice,
                                                format="mp3",
                                                speed=1.0,
                                            ),
                                            max_retries=2,
                                            base_delay=1.0,
                                        )
                                        if tts_result and tts_result.audio_data:
                                            await send_audio_chunk(
                                                tts_result.audio_data,
                                                "mp3",
                                                tts_result.duration_ms,
                                                False,
                                            )
                                            if not tts_first_audio_sent:
                                                tts_latency_ms = int((time.time() - stage_started_at) * 1000)
                                                get_event_sink().try_emit(
                                                    type="audio.first_play",
                                                    data={
                                                        "provider": tts_provider.name,
                                                        "model": getattr(tts_provider, "DEFAULT_VOICE", None),
                                                        "tts_latency_ms": tts_latency_ms,
                                                        "audio_duration_ms": tts_result.duration_ms,
                                                    },
                                                )
                                                tts_first_audio_sent = True
                                            logger.debug(f"llm_stream: sent inline TTS for clause: '{clause[:30]}...'")
                                    except Exception as e:
                                        logger.warning(f"llm_stream: inline TTS failed: {e}")
                                tts_sent_position += clause_end
                                break

            # Send completion signal on the last token
            # Note: We don't track tokens here to avoid duplication, completion is handled elsewhere

            llm_duration_ms = int((time.time() - stage_started_at) * 1000)
            if send_status:
                await send_status(
                    "llm",
                    "complete",
                    {
                        "token_count": stream_token_count,
                        "duration_ms": llm_duration_ms,
                        "provider": llm.name,
                        "model": effective_model,
                    },
                )

            get_event_sink().try_emit(
                type="llm.completed",
                data={
                    "provider": llm.name,
                    "model": effective_model,
                    "stream_token_count": stream_token_count,
                    "ttft_ms": ttft_ms,
                    "provider_call_id": str(call_row.id),
                },
            )

            # Send any remaining text to TTS
            if partial_text_queue:
                remaining = full_text[last_sent_position:].strip()
                if remaining:
                    logger.debug(f"llm_stream: queuing final remaining text for TTS: '{remaining[:50]}...'")
                    with contextlib.suppress(asyncio.QueueFull):
                        partial_text_queue.put_nowait((remaining, True))

            call_row.output_content = full_text

            return LlmStreamResult(
                full_text=full_text,
                stream_token_count=stream_token_count,
                provider=llm.name,
                model=effective_model,
                ttft_ms=ttft_ms,
                provider_call=call_row,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise LlmStreamFailure(exc, stream_token_count) from exc
