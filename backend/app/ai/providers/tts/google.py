"""Google Cloud TTS provider implementation using REST API."""

import base64
import logging
import time
from collections.abc import AsyncGenerator

import httpx

from app.ai.providers.base import TTSProvider, TTSResult
from app.ai.providers.registry import register_tts_provider

logger = logging.getLogger("tts")

# Google Cloud TTS Neural2 pricing: $16/million characters = $0.000016/char
# 0.000016 dollars = 0.0016 cents, i.e. 0.16 hundredths-of-cents per character
GOOGLE_TTS_COST_PER_CHAR_HUNDREDTHS = 0.16


@register_tts_provider
class GoogleTTSProvider(TTSProvider):
    """Google Cloud TTS provider using REST API with API key.

    Uses the texttospeech.googleapis.com REST API for synthesis.
    Supports MP3, WAV (LINEAR16), and OGG_OPUS output formats.
    """

    DEFAULT_VOICE = "male"

    # Voice presets for easy selection
    VOICE_PRESETS = {
        # Neural2 voices (best quality)
        "male": {"name": "en-US-Neural2-D", "gender": "MALE"},
        "female": {"name": "en-US-Neural2-C", "gender": "FEMALE"},
        # Standard voices (cheaper)
        "male_standard": {"name": "en-US-Standard-D", "gender": "MALE"},
        "female_standard": {"name": "en-US-Standard-C", "gender": "FEMALE"},
        # Journey voices (most natural)
        "male_journey": {"name": "en-US-Journey-D", "gender": "MALE"},
        "female_journey": {"name": "en-US-Journey-F", "gender": "FEMALE"},
    }

    # Format to Google encoding mapping
    FORMAT_ENCODINGS = {
        "mp3": "MP3",
        "wav": "LINEAR16",
        "ogg": "OGG_OPUS",
        "opus": "OGG_OPUS",
    }

    @classmethod
    def resolve_voice(cls, voice: str | None) -> str | None:
        v_raw = voice or ""
        v = v_raw.strip().lower()
        if not v:
            return cls.DEFAULT_VOICE

        # If this looks like a full Google voice ID (e.g. en-US-Neural2-D), keep it
        if "-" in v_raw and v_raw.startswith("en-"):
            return v_raw

        # Normalise preset names (case-insensitive)
        if v in cls.VOICE_PRESETS:
            return v

        # Unknown value: fall back to default preset
        return cls.DEFAULT_VOICE

    def __init__(
        self,
        api_key: str,
        default_voice: str = "male",
        timeout: float = 30.0,
    ):
        """Initialize Google TTS provider.

        Args:
            api_key: Google Cloud API key
            default_voice: Default voice preset ('male', 'female', etc.)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.default_voice = default_voice
        self.timeout = timeout
        self.base_url = "https://texttospeech.googleapis.com/v1/text:synthesize"

        self._client: httpx.AsyncClient | None = None

        logger.info(
            "Google TTS provider initialized",
            extra={
                "service": "tts",
                "provider": "google",
                "default_voice": default_voice,
                "api_key_present": bool(api_key),
            },
        )

    @property
    def name(self) -> str:
        """Provider name for logging."""
        return "google"

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        format: str = "mp3",
        speed: float = 1.0,
        **kwargs,
    ) -> TTSResult:
        """Synthesize text to speech using Google Cloud TTS API.

        Args:
            text: Text to synthesize (max 5000 chars per request)
            voice: Voice preset name or full voice ID (e.g., 'male', 'en-US-Neural2-D')
            format: Output format ('mp3', 'wav', 'ogg')
            speed: Speaking rate (0.25 to 4.0, default 1.0)
            **kwargs: Additional options:
                - pitch: Pitch adjustment (-20.0 to 20.0, default 0)
                - language_code: Override language (default: 'en-US')

        Returns:
            TTSResult with audio data, format, and duration
        """
        start_time = time.time()

        # Resolve voice configuration via class-level resolver then instance helper
        effective_voice = type(self).resolve_voice(voice)
        voice_config = self._resolve_voice(effective_voice)
        language_code = kwargs.get("language_code", "en-US")

        # Get audio encoding
        audio_encoding = self.FORMAT_ENCODINGS.get(format.lower(), "MP3")

        # Build request payload
        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": language_code,
                "name": voice_config["name"],
                "ssmlGender": voice_config["gender"],
            },
            "audioConfig": {
                "audioEncoding": audio_encoding,
                "speakingRate": max(0.25, min(4.0, speed)),
                "pitch": kwargs.get("pitch", 0),
            },
        }

        logger.debug(
            "Google TTS synthesis request",
            extra={
                "service": "tts",
                "provider": "google",
                "voice": voice_config["name"],
                "format": format,
                "text_length": len(text),
                "speed": speed,
            },
        )

        try:
            if self._client is None:
                self._client = httpx.AsyncClient(timeout=self.timeout)
            response = await self._client.post(
                self.base_url,
                params={"key": self.api_key},
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

        except httpx.TimeoutException as e:
            logger.error(
                "Google TTS request timeout",
                extra={
                    "service": "tts",
                    "provider": "google",
                    "error": str(e),
                    "timeout": self.timeout,
                },
            )
            raise

        except httpx.HTTPStatusError as e:
            logger.error(
                "Google TTS HTTP error",
                extra={
                    "service": "tts",
                    "provider": "google",
                    "status_code": e.response.status_code,
                    "error": e.response.text,
                },
            )
            raise

        # Parse response
        latency_ms = int((time.time() - start_time) * 1000)

        # Decode base64 audio content
        audio_content_b64 = result.get("audioContent", "")
        audio_data = base64.b64decode(audio_content_b64)

        # Estimate duration (rough estimate based on text length and speed)
        # Average speaking rate is ~150 words/minute = 2.5 words/second
        # Average word length is ~5 characters
        estimated_duration_ms = self._estimate_duration(text, speed)

        logger.info(
            "Google TTS synthesis complete",
            extra={
                "service": "tts",
                "provider": "google",
                "voice": voice_config["name"],
                "latency_ms": latency_ms,
                "audio_bytes": len(audio_data),
                "text_length": len(text),
                "estimated_duration_ms": estimated_duration_ms,
            },
        )

        return TTSResult(
            audio_data=audio_data,
            format=format,
            duration_ms=estimated_duration_ms,
        )

    async def stream(
        self,
        text: str,
        voice: str | None = None,
        format: str = "mp3",
        speed: float = 1.0,
        **kwargs,
    ) -> AsyncGenerator[bytes, None]:
        """Stream synthesized audio chunks.

        Note: Google Cloud TTS doesn't support true streaming via REST API.
        This implementation synthesizes the full audio and yields it in chunks.

        For true streaming, would need to use the gRPC API.

        Args:
            text: Text to synthesize
            voice: Voice preset or ID
            format: Output format
            speed: Speaking rate
            **kwargs: Additional options

        Yields:
            Audio data chunks (currently yields full audio in one chunk)
        """
        result = await self.synthesize(text, voice, format, speed, **kwargs)
        # For now, yield full audio. Could chunk it if needed.
        yield result.audio_data

    def _resolve_voice(self, voice: str | None) -> dict:
        """Resolve voice parameter to voice configuration.

        Args:
            voice: Voice preset name, full voice ID, or None

        Returns:
            Dict with 'name' and 'gender' keys
        """
        if voice is None:
            return self.VOICE_PRESETS[self.default_voice]

        # Check if it's a preset name
        if voice.lower() in self.VOICE_PRESETS:
            return self.VOICE_PRESETS[voice.lower()]

        # Check if it's a full voice ID (e.g., 'en-US-Neural2-D')
        if "-" in voice and voice.startswith("en-"):
            # Infer gender from voice ID suffix
            gender = "MALE" if voice[-1] in "ABDJ" else "FEMALE"
            return {"name": voice, "gender": gender}

        # Default fallback
        logger.warning(
            "Unknown voice, using default",
            extra={
                "service": "tts",
                "provider": "google",
                "requested_voice": voice,
                "fallback": self.default_voice,
            },
        )
        return self.VOICE_PRESETS[self.default_voice]

    @staticmethod
    def _estimate_duration(text: str, speed: float) -> int:
        """Estimate audio duration in milliseconds.

        Args:
            text: Text being synthesized
            speed: Speaking rate multiplier

        Returns:
            Estimated duration in milliseconds
        """
        # Average speaking rate: ~150 words/minute at speed=1.0
        # Average word: ~5 characters
        # So ~750 characters/minute = 12.5 chars/second at speed=1.0
        chars_per_second = 12.5 * speed
        duration_seconds = len(text) / chars_per_second
        return int(duration_seconds * 1000)

    @staticmethod
    def calculate_cost(text_length: int) -> int:
        """Calculate cost in hundredths-of-cents for text length.

        Args:
            text_length: Number of characters

        Returns:
            Cost in hundredths-of-cents (divide by 10000 for dollars)
        """
        return int(text_length * GOOGLE_TTS_COST_PER_CHAR_HUNDREDTHS)
