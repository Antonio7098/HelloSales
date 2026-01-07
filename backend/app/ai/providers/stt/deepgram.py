"""Deepgram STT provider implementation using REST API."""

import logging
import time

import httpx

from app.ai.providers.base import STTProvider, STTResult
from app.ai.providers.registry import register_stt_provider

logger = logging.getLogger("stt")

# Deepgram Nova-2 pricing: $0.0043/minute = 0.43 cents/minute
# Store in hundredths-of-cents: 43 per minute ≈ 0.7166667 per second
DEEPGRAM_COST_PER_SECOND_HUNDREDTHS = 0.7166667


@register_stt_provider
class DeepgramSTTProvider(STTProvider):
    """Deepgram Nova-2 STT provider using REST API.

    Uses the pre-recorded audio transcription endpoint for file uploads.
    Supports webm, wav, mp3, m4a, ogg, flac formats.
    """

    DEFAULT_MODEL = "nova-2"

    # Format to MIME type mapping
    FORMAT_MIME_TYPES = {
        "webm": "audio/webm",
        "wav": "audio/wav",
        "mp3": "audio/mp3",
        "m4a": "audio/m4a",
        "ogg": "audio/ogg",
        "flac": "audio/flac",
        "opus": "audio/opus",
    }

    @classmethod
    def resolve_model(cls, model: str | None) -> str:
        m = (model or "").strip()
        if not m or m.startswith("whisper-") or m.startswith("gpt-4o-transcribe"):
            return cls.DEFAULT_MODEL
        return m

    def __init__(
        self,
        api_key: str,
        model: str = "nova-2",
        timeout: float = 30.0,
    ):
        """Initialize Deepgram STT provider.

        Args:
            api_key: Deepgram API key
            model: Deepgram model (nova-2, nova, enhanced, base)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.base_url = "https://api.deepgram.com/v1/listen"

        # Reusable HTTP client for connection pooling (reduces cold-start latency)
        self._client: httpx.AsyncClient | None = None

        logger.info(
            "Deepgram STT provider initialized",
            extra={
                "service": "stt",
                "provider": "deepgram",
                "model": model,
                "api_key_present": bool(api_key),
            },
        )

    @property
    def name(self) -> str:
        """Provider name for logging."""
        return "deepgram"

    async def warm_up(self) -> None:
        """Pre-warm the HTTP connection to reduce first-request latency.

        Call this on app startup or when a user connects to reduce
        cold-start latency on the first STT request.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)

        # Make a minimal request to establish connection
        # Deepgram doesn't have a dedicated health endpoint, so we just
        # ensure the client is ready
        logger.info(
            "Deepgram STT provider warmed up",
            extra={
                "service": "stt",
                "provider": "deepgram",
            },
        )

    async def transcribe(
        self,
        audio_data: bytes,
        format: str = "webm",
        language: str = "en",
        **kwargs,
    ) -> STTResult:
        """Transcribe audio to text using Deepgram REST API.

        Args:
            audio_data: Raw audio bytes
            format: Audio format (webm, wav, mp3, m4a, ogg, flac)
            language: Language code (e.g., 'en', 'en-US')
            **kwargs: Additional Deepgram options:
                - punctuate: bool - Add punctuation (default: True)
                - smart_format: bool - Smart formatting (default: True)
                - diarize: bool - Speaker diarization (default: False)
                - utterances: bool - Split by utterance (default: False)

        Returns:
            STTResult with transcript, confidence, duration, and words
        """
        start_time = time.time()

        # Get MIME type for format
        mime_type = self.FORMAT_MIME_TYPES.get(format.lower(), "audio/webm")

        # Build query parameters
        params = {
            "model": self.model,
            "language": language,
            "punctuate": kwargs.get("punctuate", True),
            "smart_format": kwargs.get("smart_format", True),
        }

        # Optional parameters
        if kwargs.get("diarize"):
            params["diarize"] = True
        if kwargs.get("utterances"):
            params["utterances"] = True

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": mime_type,
        }

        logger.debug(
            "Deepgram transcription request",
            extra={
                "service": "stt",
                "provider": "deepgram",
                "model": self.model,
                "format": format,
                "language": language,
                "audio_bytes": len(audio_data),
            },
        )

        try:
            # Use persistent client for connection reuse
            if self._client is None:
                self._client = httpx.AsyncClient(timeout=self.timeout)

            response = await self._client.post(
                self.base_url,
                params=params,
                headers=headers,
                content=audio_data,
            )
            response.raise_for_status()
            result = response.json()

        except httpx.TimeoutException as e:
            logger.error(
                "Deepgram request timeout",
                extra={
                    "service": "stt",
                    "provider": "deepgram",
                    "error": str(e),
                    "timeout": self.timeout,
                },
            )
            raise

        except httpx.HTTPStatusError as e:
            logger.error(
                "Deepgram HTTP error",
                extra={
                    "service": "stt",
                    "provider": "deepgram",
                    "status_code": e.response.status_code,
                    "error": e.response.text,
                },
            )
            raise

        # Parse response
        duration_ms = time.time() - start_time
        stt_result = self._parse_response(result, duration_ms)

        logger.info(
            "Deepgram transcription complete",
            extra={
                "service": "stt",
                "provider": "deepgram",
                "model": self.model,
                "latency_ms": int(duration_ms * 1000),
                "audio_duration_ms": stt_result.duration_ms,
                "transcript_length": len(stt_result.transcript),
                "confidence": stt_result.confidence,
            },
        )

        return stt_result

    def _parse_response(self, result: dict, _latency_ms: float) -> STTResult:
        """Parse Deepgram API response into STTResult.

        Args:
            result: Raw API response
            _latency_ms: Request latency in milliseconds (unused, kept for interface)

        Returns:
            STTResult with parsed data
        """
        # Navigate to the transcript data
        # Structure: results -> channels[0] -> alternatives[0]
        try:
            channels = result.get("results", {}).get("channels", [])
            if not channels:
                return STTResult(
                    transcript="",
                    confidence=0.0,
                    duration_ms=0,
                    words=None,
                )

            alternatives = channels[0].get("alternatives", [])
            if not alternatives:
                return STTResult(
                    transcript="",
                    confidence=0.0,
                    duration_ms=0,
                    words=None,
                )

            best_alternative = alternatives[0]
            transcript = best_alternative.get("transcript", "")
            confidence = best_alternative.get("confidence", 0.0)

            # Parse word-level timestamps
            words = None
            raw_words = best_alternative.get("words", [])
            if raw_words:
                words = [
                    {
                        "word": w.get("word", ""),
                        "start": w.get("start", 0.0),
                        "end": w.get("end", 0.0),
                        "confidence": w.get("confidence", 0.0),
                    }
                    for w in raw_words
                ]

            # Get audio duration from metadata
            metadata = result.get("metadata", {})
            duration_seconds = metadata.get("duration", 0)
            duration_ms = int(duration_seconds * 1000) if duration_seconds else None

            return STTResult(
                transcript=transcript,
                confidence=confidence,
                duration_ms=duration_ms,
                words=words,
            )

        except (KeyError, IndexError, TypeError) as e:
            logger.warning(
                "Error parsing Deepgram response",
                extra={
                    "service": "stt",
                    "provider": "deepgram",
                    "error": str(e),
                    "response_keys": list(result.keys()) if result else None,
                },
            )
            return STTResult(
                transcript="",
                confidence=0.0,
                duration_ms=0,
                words=None,
            )

    @staticmethod
    def calculate_cost(duration_ms: int) -> int:
        """Calculate cost in hundredths-of-cents for audio duration.

        Args:
            duration_ms: Audio duration in milliseconds

        Returns:
            Cost in hundredths-of-cents (divide by 10000 for dollars)
        """
        duration_seconds = duration_ms / 1000
        return int(duration_seconds * DEEPGRAM_COST_PER_SECOND_HUNDREDTHS)
