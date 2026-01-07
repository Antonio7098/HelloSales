"""Voice service for handling voice-to-voice conversations.

Orchestrates the STT → LLM → TTS pipeline for voice interactions.
"""

import asyncio
import contextlib
import inspect
import logging
import random
import time
import uuid
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import STTProvider, TTSProvider
from app.ai.substrate import PipelineRunLogger, ProviderCallLogger
from app.ai.substrate.agent.context_snapshot import ContextSnapshot
from app.ai.substrate.stages import (
    PipelineContext,
    PipelineOrchestrator,
    StageExecutionError,
    StageResult,
)
from app.ai.substrate.stages.base import create_stage_context
from app.ai.substrate.stages.graph import UnifiedPipelineCancelled
from app.ai.substrate.stages.inputs import create_stage_inputs
from app.ai.substrate.stages.ports import create_stage_ports
from app.config import get_settings
from app.core.di import get_container
from app.domains.assessment.pipeline import backfill_interaction_id
from app.domains.chat.service import ChatService
from app.models import Interaction

logger = logging.getLogger("voice")

DEBUG_LOG_PATH = "/tmp/debug_voice_handler.log"

def _debug_log(message: str) -> None:  # pragma: no cover - diagnostics only
    try:
        with open(DEBUG_LOG_PATH, "a") as f:
            f.write(f"[{datetime.now(UTC)}] {message}\n")
    except Exception:
        logger.debug("Failed to write voice debug log", exc_info=True)


def now_ms() -> int:
    """Return current time in milliseconds for timing logs."""
    return int(time.time() * 1000)


T = TypeVar("T")


async def _retry_with_backoff(
    func: Callable[[], Any],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
) -> T:
    """Retry an async function with exponential backoff on network-related failures.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Exponential backoff multiplier
        jitter: Add random jitter to delay

    Returns:
        Result of the function call

    Raises:
        The last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            result = func()

            # Async generators can't be awaited; return them directly so callers can iterate.
            if isinstance(result, AsyncGenerator):
                return result  # type: ignore[return-value]

            if inspect.isawaitable(result):
                return await result

            return result
        except Exception as e:
            last_exception = e

            # Check if this is a retryable network error
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

            # Don't retry on the last attempt or non-retryable errors
            if attempt >= max_retries or not is_retryable:
                raise e

            # Calculate delay with exponential backoff
            delay = min(base_delay * (backoff_factor**attempt), max_delay)
            if jitter:
                delay = delay * (0.5 + random.random() * 0.5)  # Add 50% jitter

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

    # This should never be reached, but just in case
    raise last_exception or RuntimeError("Unexpected retry logic failure")


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


async def _safe_call(coro):
    """Safely call an async coroutine, logging any exceptions."""
    try:
        await coro
    except Exception as e:
        logger.warning(f"Async task failed: {e}", exc_info=True)


@dataclass
class RecordingState:
    """State for an active recording."""

    session_id: uuid.UUID
    user_id: uuid.UUID
    format: str = "webm"
    chunks: list[bytes] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    # Optional skill IDs supplied by frontend for this recording
    skill_ids: list[uuid.UUID] | None = None
    # Optional background task for enricher prefetch (to reduce latency)
    enricher_prefetch_task: asyncio.Task | None = None


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

    # Cancellation status (for graceful early termination, e.g., no speech detected)
    cancelled: bool = False
    cancelled_reason: str | None = None

    @property
    def total_cost(self) -> int:
        """Total cost in hundredths-of-cents."""
        return self.stt_cost + self.llm_cost + self.tts_cost


class VoiceService:
    """Service for handling voice conversations.

    Manages recording state and orchestrates the full STT → LLM → TTS pipeline.
    """

    def __init__(
        self,
        db: AsyncSession | None,
        stt_provider: STTProvider | None = None,
        tts_provider: TTSProvider | None = None,
        chat_service: ChatService | None = None,
    ):
        """Initialize voice service.

        Args:
            db: Database session (can be None if passed to methods)
            stt_provider: STT provider (defaults to configured provider via DI container)
            tts_provider: TTS provider (defaults to configured provider via DI container)
            chat_service: Chat service for LLM handling (defaults to new instance)
        """
        self.db = db
        container = get_container()
        self.stt = stt_provider or container.stt_provider
        self.tts = tts_provider or container.tts_provider
        self.chat = chat_service  # Will be created with db when needed
        self.call_logger = None  # Will be created with db when needed
        self.pipeline_logger = None  # Will be created with db when needed

        # Active recordings by user_id
        self._recordings: dict[uuid.UUID, RecordingState] = {}
        self._pending_chunks: dict[uuid.UUID, list[bytes]] = {}

        # Active pipeline contexts by user_id for cancellation
        self._active_pipelines: dict[uuid.UUID, PipelineContext] = {}

    def _ensure_db_components(self, db: AsyncSession) -> None:
        """Ensure database-dependent components are created with the given session."""
        if self.db != db or self.call_logger is None:
            self.db = db
            # Only create new ChatService if one doesn't exist (preserve mock in tests)
            if self.chat is None:
                container = get_container()
                self.chat = container.create_chat_service(db=db)
            self.call_logger = ProviderCallLogger(db)
            self.pipeline_logger = PipelineRunLogger(db)

    # Threshold for forcing TTS even without sentence-ending punctuation
    EARLY_TTS_CHAR_THRESHOLD = 80

    @staticmethod
    def _filter_spoken_punctuation(text: str) -> str:
        """Filter out literal spoken punctuation names like 'quote mark' or 'asterisk'.

        These appear when the LLM literally narrates punctuation characters.
        We remove them before TTS to prevent the voice from speaking them.
        """
        import re

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

        # Join all patterns with | and compile with case-insensitive flag
        combined_pattern = re.compile("|".join(patterns), re.IGNORECASE)

        # Replace all matches with empty string
        filtered = combined_pattern.sub("", text)

        # Clean up extra whitespace that may result from removals
        filtered = re.sub(r"\s+", " ", filtered).strip()

        return filtered

    async def _run_llm_and_tts_stage(self, ctx: PipelineContext) -> StageResult:
        """Deprecated: LLM/TTS are fully handled by Voice stages (LlmStreamStage, TtsIncrementalStage)."""
        raise NotImplementedError("Deprecated helper; use stage graph with LlmStreamStage/TtsIncrementalStage")

    @staticmethod
    def _sanitize_for_tts(text: str) -> str:
        """Sanitize text before TTS to avoid speaking formatting characters.

        - Removes markdown emphasis/code markers like asterisks and backticks
        - Removes double quotes (straight and curly)
        - Applies spoken punctuation filter to remove phrases like "quote mark"
        - Normalizes whitespace
        """
        import re

        if not text:
            return text

        s = text
        # Remove markdown/code markers
        s = s.replace("`", "")
        s = s.replace("*", "")
        # Remove double quotes (keep apostrophes for contractions)
        s = re.sub(r"[\"“”]", "", s)

        # Remove any literal spoken punctuation phrases
        s = VoiceService._filter_spoken_punctuation(s)

        # Normalize whitespace
        s = re.sub(r"\s+", " ", s).strip()
        return s

    @staticmethod
    def _extract_complete_sentences(text: str) -> tuple[str, str]:
        """Extract complete sentences from text buffer.

        Returns (sentences_to_speak, remaining_buffer).
        A sentence is considered complete when it ends with . ! or ?
        followed by a space or end of string.

        Also triggers early TTS if buffer exceeds threshold and has a clause
        boundary (comma, colon, semicolon) to reduce time-to-first-audio.
        """
        import re

        # Filter out literal spoken punctuation names before processing
        text = VoiceService._filter_spoken_punctuation(text)

        # Find all positions where a sentence ends (. ! ? followed by space or end)
        pattern = r"([.!?])(?:\s+|$)"

        last_end = 0
        sentences = []

        for match in re.finditer(pattern, text):
            # Include up to and including the punctuation
            end_pos = match.end(1)
            sentences.append(text[last_end:end_pos])
            # Skip any whitespace after punctuation
            last_end = match.end()

        if sentences:
            complete = " ".join(s.strip() for s in sentences if s.strip())
            remaining = text[last_end:] if last_end < len(text) else ""
            return complete, remaining

        # Early TTS fallback: if buffer is long, try to break at clause boundary
        if len(text) >= VoiceService.EARLY_TTS_CHAR_THRESHOLD:
            # Look for clause boundaries: comma, colon, semicolon followed by space
            clause_pattern = r"([,:;])(?:\s+)"
            matches = list(re.finditer(clause_pattern, text))
            if matches:
                # Use the last clause boundary to maximize chunk size
                last_match = matches[-1]
                end_pos = last_match.end(1)
                to_speak = text[:end_pos].strip()
                remaining = text[last_match.end() :].strip()
                if to_speak:
                    return to_speak, remaining

            # Fallback: if there's no clear clause boundary, break on the last
            # whitespace before the threshold to avoid waiting indefinitely
            # for punctuation in very long sentences.
            last_space = text.rfind(" ", 0, VoiceService.EARLY_TTS_CHAR_THRESHOLD)
            if last_space > 0:
                to_speak = text[:last_space].strip()
                remaining = text[last_space + 1 :].strip()
                if to_speak:
                    return to_speak, remaining

        return "", text

    def start_recording(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        audio_format: str = "webm",
        skill_ids: list[uuid.UUID] | None = None,
        enricher_prefetch_task: asyncio.Task | None = None,
    ) -> None:
        """Start a new recording for a user.

        Args:
            session_id: Session ID
            user_id: User ID
            audio_format: Audio format (webm, wav, mp3, m4a)
        """
        # Cancel any existing recording for this user
        if user_id in self._recordings:
            logger.warning(
                "Replacing existing recording",
                extra={
                    "service": "voice",
                    "user_id": str(user_id),
                    "old_session_id": str(self._recordings[user_id].session_id),
                    "new_session_id": str(session_id),
                },
            )

        self._recordings[user_id] = RecordingState(
            session_id=session_id,
            user_id=user_id,
            format=audio_format,
            skill_ids=skill_ids,
            enricher_prefetch_task=enricher_prefetch_task,
        )

        # Flush any chunks that arrived before start_recording completed
        pending = self._pending_chunks.pop(user_id, None)
        if pending:
            self._recordings[user_id].chunks.extend(pending)

        logger.info(
            "Recording started",
            extra={
                "service": "voice",
                "session_id": str(session_id),
                "user_id": str(user_id),
                "format": audio_format,
            },
        )

    def add_chunk(self, user_id: uuid.UUID, chunk_data: bytes) -> bool:
        """Add an audio chunk to the current recording.

        Args:
            user_id: User ID
            chunk_data: Raw audio bytes

        Returns:
            True if chunk was added, False if no active recording
        """
        if user_id not in self._recordings:
            # Buffer chunks until start_recording finishes
            if user_id not in self._pending_chunks:
                self._pending_chunks[user_id] = []
            self._pending_chunks[user_id].append(chunk_data)
            logger.info(
                "Chunk buffered (no active recording yet)",
                extra={
                    "service": "voice",
                    "user_id": str(user_id),
                    "chunk_size": len(chunk_data),
                    "pending_count": len(self._pending_chunks[user_id]),
                },
            )
            return False

        self._recordings[user_id].chunks.append(chunk_data)

        logger.debug(
            "Audio chunk added",
            extra={
                "service": "voice",
                "user_id": str(user_id),
                "chunk_size": len(chunk_data),
                "total_chunks": len(self._recordings[user_id].chunks),
            },
        )

        return True

    def cancel_recording(self, user_id: uuid.UUID) -> bool:
        """Cancel the current recording for a user.

        Args:
            user_id: User ID

        Returns:
            True if recording was cancelled, False if none active
        """
        if user_id not in self._recordings:
            return False

        recording = self._recordings.pop(user_id)

        logger.info(
            "Recording cancelled",
            extra={
                "service": "voice",
                "user_id": str(user_id),
                "session_id": str(recording.session_id),
                "chunks_discarded": len(recording.chunks),
            },
        )

        return True

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

        # Mark pipeline as canceled
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

    def get_recording_state(self, user_id: uuid.UUID) -> RecordingState | None:
        """Get the current recording state for a user."""
        return self._recordings.get(user_id)

    async def process_recording(
        self,
        user_id: uuid.UUID,
        message_id: uuid.UUID | None = None,
        pipeline_run_id: uuid.UUID | None = None,
        request_id: uuid.UUID | None = None,
        org_id: uuid.UUID | None = None,
        topology: str = "voice_fast",
        send_status: Callable[[str, str, dict[str, Any] | None], Any] | None = None,
        send_token: Callable[[str], Any] | None = None,
        send_transcript: Callable[[uuid.UUID, str, float, int], Any] | None = None,
        send_audio_chunk: Callable[[bytes, str, int, bool], Any] | None = None,
        on_interaction_saved: Callable[[uuid.UUID, str], Any] | None = None,  # noqa: ARG002
        model_id: str | None = None,
        platform: str | None = None,
        behavior: str | None = None,
    ) -> VoicePipelineResult:
        """Process the recorded audio through the full pipeline.

        This is the main entry point after recording ends.
        Runs: STT → LLM (with streaming + incremental TTS) → final audio

        Args:
            user_id: User ID
            message_id: Client-generated message ID for deduplication
            send_status: Callback to send status updates
            send_token: Callback to send streamed LLM tokens
            send_transcript: Callback to send transcript immediately after STT
                             (message_id, transcript, confidence, duration_ms)
            send_audio_chunk: Callback to send TTS audio chunks as sentences complete
                              (audio_data, format, duration_ms, is_final)
            model_id: Override LLM model ID (None = use provider default)

        Returns:
            VoicePipelineResult with all outputs

        Raises:
            ValueError: If no active recording for user
        """
        if user_id not in self._recordings:
            raise ValueError(f"No active recording for user {user_id}")

        # Ensure database components are initialized with the current db session
        if self.db is not None:
            self._ensure_db_components(self.db)

        try:
            with open("/tmp/debug_voice_handler.log", "a") as f:
                f.write(f"\n[{now_ms()}] process_recording called for user_id={user_id}\n")
        except Exception:
            pass

        logger.error(f"[DEBUG_LOG] process_recording called for user_id={user_id}")
        recording = self._recordings.pop(user_id)
        message_id = message_id or uuid.uuid4()
        assistant_message_id = uuid.uuid4()
        pipeline_start = time.time()
        pipeline_start_ts = _utcnow_iso()

        # TIMING: Track pipeline stages
        logger.info(
            "[TIMING] Pipeline started",
            extra={
                "service": "voice",
                "timing": "pipeline_start",
                "session_id": str(recording.session_id),
                "t_ms": 0,
            },
        )

        stt_provider_call_id: uuid.UUID | None = None
        llm_provider_call_id: uuid.UUID | None = None
        tts_provider_call_id: uuid.UUID | None = None

        # Stage timestamps (ISO8601)
        llm_first_token_ts: str | None = None
        llm_first_chunk_ts: str | None = None
        tts_first_audio_ts: str | None = None
        pipeline_end_ts: str | None = None

        # Timing metrics
        ttft_ms: int | None = None
        ttfa_ms: int | None = None
        ttfc_ms: int | None = None
        tokens_per_second: int | None = None

        logger.info(
            "Processing voice pipeline",
            extra={
                "service": "voice",
                "session_id": str(recording.session_id),
                "user_id": str(user_id),
                "message_id": str(message_id),
                "chunks": len(recording.chunks),
                "format": recording.format,
            },
        )

        audio_data = b"".join(recording.chunks)

        settings = get_settings()
        effective_behavior = behavior or settings.pipeline_mode or "fast"

        effective_behavior = "accurate" if "accurate" in topology else "fast"

        ctx_data: dict[str, Any] = {
            "recording": recording,
            "audio_data": audio_data,
            "send_status": send_status,
            "send_token": send_token,
            "send_audio_chunk": send_audio_chunk,
            "send_transcript": send_transcript,
            "request_id": request_id,
            "pipeline_run_id": pipeline_run_id,
            "org_id": org_id,
            "user_id": recording.user_id,
            "session_id": recording.session_id,
            "model_id": model_id,
            "platform": platform,
            "behavior": effective_behavior,
            "topology": topology,
            "trigger": "voice.end",
            "service": "voice",
            "db": self.db,
            "chat_service": self.chat,
            "llm_provider": self.chat.llm,
            "tts_provider": self.tts,
            "stt_provider": self.stt,  # Added for stage dependency injection
            "call_logger": self.call_logger,
            "retry_fn": _retry_with_backoff,
        }

        # Set required context data for stages
        ctx_data["audio_data"] = audio_data
        ctx_data["recording"] = recording
        ctx_data["message_id"] = (
            message_id  # Pass message_id to context for UserMessagePersistStage
        )
        # Ensure send_audio_chunk is available for TtsIncrementalStage
        ctx_data["send_audio_chunk"] = send_audio_chunk

        pipeline_ctx = PipelineContext(
            pipeline_run_id=pipeline_run_id,
            request_id=request_id,
            session_id=recording.session_id,
            user_id=user_id,
            org_id=org_id,
            interaction_id=message_id,
            topology=topology,
            configuration={},
            behavior=effective_behavior,
            service="voice",
            data=ctx_data,
            db=self.db,
        )

        # Store pipeline context for cancellation support
        self._active_pipelines[user_id] = pipeline_ctx

        # Create pipeline from registry (auto-registers on first access)
        from app.ai.substrate.stages.pipeline_registry import pipeline_registry
        pipeline = pipeline_registry.get(topology)
        graph = pipeline.build()
        _debug_log(f"Unified pipeline created with {len(graph.stage_specs)} stages")

        _debug_log(
            f"process_recording start user_id={user_id} message_id={message_id} stages={len(graph.stage_specs)}"
        )
        print(f"[DEBUG] Voice pipeline starting with {len(graph.stage_specs)} stages")
        logger.info(f"[VOICE_PIPELINE] Starting pipeline with {len(graph.stage_specs)} stages")

        _debug_log("About to call Kernel orchestrator")
        orchestrator = PipelineOrchestrator()

        async def _runner(send_status_cb, send_token_cb):
            pipeline_ctx.data["send_status"] = send_status_cb
            pipeline_ctx.data["send_token"] = send_token_cb

            topology = pipeline_ctx.topology or ""
            channel = pipeline_ctx.configuration.get("channel") or "voice_channel"

            snapshot = ContextSnapshot(
                pipeline_run_id=pipeline_ctx.pipeline_run_id,
                request_id=pipeline_ctx.request_id,
                session_id=pipeline_ctx.session_id,
                user_id=pipeline_ctx.user_id,
                org_id=pipeline_ctx.org_id,
                interaction_id=pipeline_ctx.interaction_id,
                topology=topology,
                channel=channel,
                behavior=pipeline_ctx.behavior,
                input_text=pipeline_ctx.data.get("transcript", ""),
                messages=[],
            )

            recording_obj = pipeline_ctx.data.get("recording")

            # Create queue for streaming partial text from LLM to TTS
            partial_text_queue: asyncio.Queue[tuple[str, bool]] | None = None
            with contextlib.suppress(Exception):
                partial_text_queue = asyncio.Queue(maxsize=100)

            ports = create_stage_ports(
                db=self.db,
                send_status=send_status_cb,
                send_token=send_token_cb,
                send_audio_chunk=pipeline_ctx.data.get("send_audio_chunk"),
                send_transcript=pipeline_ctx.data.get("send_transcript"),
                recording=recording_obj,
                audio_data=pipeline_ctx.data.get("audio_data"),
                audio_format=recording_obj.format if recording_obj else None,
                chat_service=pipeline_ctx.data.get("chat_service"),
                partial_text_queue=partial_text_queue,
            )

            inputs = create_stage_inputs(
                snapshot=snapshot,
                ports=ports,
            )

            stage_ctx = create_stage_context(snapshot=snapshot, config={"inputs": inputs, "data": dict(pipeline_ctx.data)})

            results = await graph.run(stage_ctx)

            def _serialize_for_json(obj: Any) -> Any:
                """Recursively serialize objects for JSON, handling non-serializable types."""
                if obj is None or isinstance(obj, (str, int, float, bool)):
                    return obj
                if isinstance(obj, bytes):
                    return {"__type__": "bytes", "data": "[BINARY_DATA]"}
                if isinstance(obj, dict):
                    return {str(k): _serialize_for_json(v) for k, v in obj.items()}
                if isinstance(obj, (list, tuple)):
                    return [_serialize_for_json(item) for item in obj]
                if hasattr(obj, "to_dict") and callable(obj.to_dict):
                    return _serialize_for_json(obj.to_dict())
                if hasattr(obj, "__dict__"):
                    return _serialize_for_json(obj.__dict__)
                return str(obj)

            results_serializable = {
                name: {
                    "status": output.status.value,
                    "data": _serialize_for_json(output.data),
                    "error": output.error,
                }
                for name, output in results.items()
            }

            return {
                "success": True,
                "stages_completed": list(results.keys()),
                "results": results_serializable,
            }

        try:
            stage_results = await orchestrator.run(
                pipeline_run_id=pipeline_run_id or uuid.uuid4(),
                service="voice",
                topology=topology,
                behavior=pipeline_ctx.behavior,
                trigger="voice_input",
                request_id=request_id or uuid.uuid4(),
                session_id=recording.session_id,
                user_id=user_id,
                org_id=org_id,
                send_status=send_status or (lambda *_args, **_kw: asyncio.sleep(0)),
                send_token=send_token or (lambda *_args, **_kw: asyncio.sleep(0)),
                runner=_runner,
            )

            _debug_log(f"voice_pipeline completed stages={list(stage_results.get('stages_completed', []))}")
            print(f"[DEBUG] Voice pipeline completed with stages: {list(stage_results.get('stages_completed', []))}")
            logger.info(
                f"[VOICE_PIPELINE] Pipeline completed with results: {list(stage_results.get('stages_completed', []))}"
            )

            results = stage_results.get("results", {})

            stt_provider_call_id = None
            llm_provider_call_id = None
            tts_provider_call_id = None

            stt_transcript = None
            stt_confidence = None
            stt_duration_ms = None
            stt_cost = 0
            stt_latency_ms = 0

            full_response = ""
            token_count = 0
            llm_cost = 0
            llm_latency_ms = 0
            ttft_ms = None
            ttfc_ms = None
            tokens_per_second = None

            final_audio = b""
            total_tts_duration_ms = 0
            tts_cost = 0
            tts_latency_ms = 0

            for stage_name, stage_data in results.items():
                stage_data_dict = stage_data.get("data", {}) if isinstance(stage_data, dict) else {}
                status = stage_data.get("status") if isinstance(stage_data, dict) else None

                if stage_name in ("stt", "unified_stt") and status == "ok":
                    stt_provider_call_id = stage_data_dict.get("stt_provider_call_id")
                    stt_transcript = stage_data_dict.get("transcript")
                    stt_confidence = stage_data_dict.get("confidence")
                    stt_duration_ms = stage_data_dict.get("duration_ms")
                    stt_cost = stage_data_dict.get("cost_cents", 0)
                    stt_latency_ms = stage_data_dict.get("latency_ms", 0)

                elif stage_name in ("llm", "llm_stream", "unified_llm") and status == "ok":
                    llm_provider_call_id = stage_data_dict.get("llm_provider_call_id")
                    full_response = stage_data_dict.get("response", "")
                    token_count = stage_data_dict.get("stream_token_count", 0)
                    llm_cost = stage_data_dict.get("cost_cents", 0)
                    llm_latency_ms = stage_data_dict.get("latency_ms", 0)
                    ttft_ms = stage_data_dict.get("ttft_ms")
                    ttfc_ms = stage_data_dict.get("ttfc_ms")
                    tokens_per_second = stage_data_dict.get("tokens_per_second")

                elif stage_name in ("tts", "tts_incremental", "unified_tts") and status == "ok":
                    tts_provider_call_id = stage_data_dict.get("tts_provider_call_id")
                    audio_data_str = stage_data_dict.get("audio_data", "")
                    if isinstance(audio_data_str, str):
                        try:
                            final_audio = audio_data_str.encode("latin-1") if audio_data_str else b""
                        except UnicodeEncodeError:
                            final_audio = b""
                    total_tts_duration_ms = stage_data_dict.get("audio_duration_ms", 0)
                    tts_cost = stage_data_dict.get("tts_cost_cents", 0)
                    tts_latency_ms = stage_data_dict.get("tts_latency_ms", 0)

            _debug_log(f"Extracted stt_provider_call_id: {stt_provider_call_id is not None}")
            _debug_log(f"Extracted stt_transcript: {stt_transcript is not None}")

            if not stt_provider_call_id:
                _debug_log(f"Available stages in results: {list(results.keys())}")

            _debug_log("Post-flight validation passed")
            logger.info(
                "[VOICE_PIPELINE] Post-flight validation passed: all critical stages completed",
                extra={
                    "service": "voice",
                    "session_id": str(recording.session_id),
                },
            )
        except UnifiedPipelineCancelled as exc:
            logger.info(
                "Voice pipeline cancelled",
                extra={
                    "service": "voice",
                    "session_id": str(recording.session_id),
                    "user_id": str(user_id),
                    "cancelled_by": exc.stage,
                    "reason": exc.reason,
                    "stages_completed": list(exc.results.keys()),
                },
            )
            # Return result with cancelled flag for graceful early termination
            return VoicePipelineResult(
                transcript="",
                transcript_confidence=0.0,
                audio_duration_ms=0,
                response_text="",
                llm_latency_ms=0,
                audio_data=b"",
                audio_format="",
                tts_duration_ms=0,
                user_message_id=message_id or uuid.UUID(int=0),
                assistant_message_id=uuid.UUID(int=0),
                stt_cost=0,
                llm_cost=0,
                tts_cost=0,
                cancelled=True,
                cancelled_reason=exc.reason,
            )
        except StageExecutionError as exc:
            logger.error(
                "Voice pipeline stage failed",
                extra={
                    "service": "voice",
                    "session_id": str(recording.session_id),
                    "user_id": str(user_id),
                    "failed_stage": exc.stage,
                },
                exc_info=True,
            )
            raise RuntimeError(f"Voice pipeline failed during stage '{exc.stage}'") from exc
        except Exception as e:
            _debug_log(f"Unexpected exception in pipeline: {type(e).__name__}: {str(e)}")
            logger.error(
                "Unexpected exception in voice pipeline",
                extra={
                    "service": "voice",
                    "session_id": str(recording.session_id),
                    "user_id": str(user_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise
        finally:
            self._active_pipelines.pop(user_id, None)
            _debug_log("Finally block about to complete")

        _debug_log("After finally block - extracting stage results")

        logger.info(
            f"[DEBUG] STT output: transcript='{stt_transcript}', confidence={stt_confidence}"
        )

        logger.info(
            "[TIMING][backend] stt.finished",
            extra={
                "service": "voice",
                "t": now_ms(),
                "session_id": str(recording.session_id),
                "request_id": str(request_id) if request_id else None,
                "pipeline_run_id": str(pipeline_run_id) if pipeline_run_id else None,
                "stt_latency_ms": stt_latency_ms,
                "transcript_length": len(stt_transcript) if stt_transcript else 0,
                "confidence": stt_confidence,
                "audio_duration_ms": stt_duration_ms,
            },
        )

        estimated_tokens_in = 0
        estimated_tokens_out = 0

        # ========== FINAL COMMIT: Batch all DB operations ==========
        try:
            # Commit all pipeline events and interactions first
            await self.db.commit()
            logger.info(
                "Voice pipeline: Events and interactions committed",
                extra={
                    "service": "voice",
                    "session_id": str(recording.session_id),
                    "user_id": str(user_id),
                },
            )

            # Backfill interaction_id on any assessment records created during
            # background assessment (they were created without interaction_id
            # because the interaction wasn't committed yet)
            await backfill_interaction_id(
                db=self.db,
                session_id=recording.session_id,
                interaction_id=message_id,
            )
            await self.db.commit()  # Commit the backfill updates
            logger.info(
                "Voice pipeline: Persist + backfill committed",
                extra={
                    "service": "voice",
                    "session_id": str(recording.session_id),
                    "user_id": str(user_id),
                },
            )

        except Exception as e:  # pragma: no cover - defensive
            logger.error(
                "Final commit failed in voice pipeline",
                extra={
                    "service": "voice",
                    "session_id": str(recording.session_id),
                    "user_id": str(user_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

        # Pipeline complete
        pipeline_end_ts = _utcnow_iso()
        total_latency_ms = int((time.time() - pipeline_start) * 1000)

        logger.info(
            "[TIMING][backend] pipeline.completed",
            extra={
                "service": "voice",
                "t": now_ms(),
                "session_id": str(recording.session_id),
                "request_id": str(request_id) if request_id else None,
                "pipeline_run_id": str(pipeline_run_id) if pipeline_run_id else None,
                "total_latency_ms": total_latency_ms,
                "stt_latency_ms": stt_latency_ms,
                "llm_latency_ms": llm_latency_ms,
                "tts_latency_ms": tts_latency_ms,
                "ttft_ms": ttft_ms,
                "ttfa_ms": ttfa_ms,
                "ttfc_ms": ttfc_ms,
                "token_count": token_count,
            },
        )

        # Persist aggregated pipeline metrics in pipeline_runs
        try:
            total_cost_cents = (stt_cost or 0) + (llm_cost or 0) + (tts_cost or 0)

            stages = {
                "pipeline": {
                    "start_at": pipeline_start_ts,
                    "end_at": pipeline_end_ts,
                    "total_ms": total_latency_ms,
                    "ttfa_ms": ttfa_ms,
                },
                "stt": {
                    "start_at": None,
                    "end_at": None,
                    "latency_ms": stt_latency_ms,
                    "audio_duration_ms": stt_duration_ms,
                },
                "llm": {
                    "start_at": None,
                    "end_at": None,
                    "first_token_at": llm_first_token_ts,
                    "first_chunk_at": llm_first_chunk_ts,
                    "latency_ms": llm_latency_ms,
                    "ttft_ms": ttft_ms,
                    "ttfc_ms": ttfc_ms,
                    "token_count": token_count,
                    "tokens_per_second": (tokens_per_second / 100.0)
                    if tokens_per_second is not None
                    else None,
                },
                "tts": {
                    "start_at": None,
                    "end_at": None,
                    "first_audio_at": tts_first_audio_ts,
                    "latency_ms": tts_latency_ms,
                    "total_tts_duration_ms": total_tts_duration_ms,
                    "incremental": bool(send_audio_chunk),
                    "first_audio_sent": None,
                },
            }
            await self.pipeline_logger.log_run(
                pipeline_run_id=pipeline_run_id,
                service="voice",
                request_id=request_id,
                org_id=org_id,
                session_id=recording.session_id,
                user_id=recording.user_id,
                interaction_id=None,
                stt_provider_call_id=stt_provider_call_id,
                llm_provider_call_id=llm_provider_call_id,
                tts_provider_call_id=tts_provider_call_id,
                total_latency_ms=total_latency_ms,
                ttft_ms=ttft_ms,
                ttfa_ms=ttfa_ms,
                ttfc_ms=ttfc_ms,
                tokens_in=estimated_tokens_in,
                tokens_out=estimated_tokens_out,
                input_audio_duration_ms=stt_duration_ms,
                output_audio_duration_ms=total_tts_duration_ms,
                tts_chunk_count=1,
                total_cost_cents=total_cost_cents,
                tokens_per_second=tokens_per_second,
                success=True,
                error=None,
                stages=stages,
                metadata={"topology": topology},
            )
            await self.db.commit()
        except Exception:  # pragma: no cover - defensive
            logger.exception("Failed to log pipeline run")

        return VoicePipelineResult(
            transcript=stt_transcript or "",
            transcript_confidence=stt_confidence or 0.0,
            audio_duration_ms=stt_duration_ms or 0,
            response_text=full_response,
            llm_latency_ms=llm_latency_ms,
            audio_data=final_audio,
            audio_format="mp3",
            tts_duration_ms=total_tts_duration_ms,
            user_message_id=message_id,
            assistant_message_id=assistant_message_id,
            stt_cost=stt_cost,
            llm_cost=llm_cost,
            tts_cost=tts_cost,
        )

    async def _save_voice_interaction(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        message_id: uuid.UUID,
        transcript: str | None = None,
        audio_duration_ms: int | None = None,
        stt_provider_call_id: uuid.UUID | None = None,
        llm_provider_call_id: uuid.UUID | None = None,
        tts_provider_call_id: uuid.UUID | None = None,
        commit: bool = True,
    ) -> Interaction:
        """Save a voice interaction to the database.

        Args:
            session_id: Session ID
            role: 'user' or 'assistant'
            content: Text content (transcript for user, response for assistant)
            message_id: Message ID
            transcript: STT transcript (for user messages)
            audio_duration_ms: Audio duration in ms (for user messages)
            stt_cost_cents: STT cost in hundredths-of-cents
            tts_cost_cents: TTS cost in hundredths-of-cents
            latency_ms: LLM latency (for assistant messages)
            tokens_in: Input tokens (for assistant messages)
            tokens_out: Output tokens (for assistant messages)
            llm_cost_cents: LLM cost in hundredths-of-cents

        Returns:
            The saved Interaction
        """
        interaction = Interaction(
            id=message_id,
            session_id=session_id,
            message_id=message_id,
            role=role,
            content=content,
            input_type="voice" if role == "user" else None,
            transcript=transcript,
            audio_duration_ms=audio_duration_ms,
            stt_provider_call_id=stt_provider_call_id,
            llm_provider_call_id=llm_provider_call_id,
            tts_provider_call_id=tts_provider_call_id,
        )
        self.db.add(interaction)
        if commit:
            await self.db.commit()
            await self.db.refresh(interaction)
        else:
            # Just flush to get the ID but don't commit yet
            await self.db.flush()

        logger.debug(
            "Voice interaction saved",
            extra={
                "service": "voice",
                "session_id": str(session_id),
                "interaction_id": str(interaction.id),
                "role": role,
                "audio_duration_ms": audio_duration_ms,
            },
        )

        return interaction
