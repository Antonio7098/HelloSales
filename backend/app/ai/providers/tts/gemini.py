from __future__ import annotations

import asyncio
import logging

from app.ai.providers.base import TTSProvider, TTSResult
from app.ai.providers.registry import register_tts_provider

logger = logging.getLogger("tts")


@register_tts_provider
class GeminiFlashTTSProvider(TTSProvider):
    """Gemini 2.5 Flash TTS provider using the google-genai client.

    This provider uses the Gemini-TTS models, which bill based on input text
    tokens and output audio tokens. Pricing is handled separately in the
    pricing helpers; this class focuses purely on synthesis.
    """

    DEFAULT_VOICE = "Kore"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self.api_key = api_key
        # Default Gemini TTS model; can be overridden if needed.
        self.model = model or "gemini-2.5-flash-tts"

    @property
    def name(self) -> str:
        """Provider name for logging and pricing selection."""

        # Important: include "gemini" so pricing logic can detect this
        # as a Gemini-based TTS provider.
        return "gemini_tts"

    @classmethod
    def resolve_voice(cls, voice: str | None) -> str | None:
        """Resolve a voice identifier for Gemini TTS.

        For now we map simple aliases (e.g. "male", "female") to a
        default prebuilt Gemini voice, and otherwise pass through.
        """

        v_raw = voice or ""
        v = v_raw.strip()
        if not v:
            return cls.DEFAULT_VOICE

        # Simple aliases map to the default voice for now.
        if v.lower() in {"male", "female", "default"}:
            return cls.DEFAULT_VOICE

        # Assume caller provided a full Gemini voice name.
        return v_raw

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        format: str = "mp3",
        speed: float = 1.0,
        **_: object,
    ) -> TTSResult:
        """Synthesize text to speech using Gemini 2.5 Flash TTS.

        The underlying API currently uses the google-genai client
        (imported as google.genai). We call it synchronously in a
        background thread for compatibility with our async interface.
        """

        try:
            import google.genai as genai
            from google.genai import types
        except ImportError as e:  # pragma: no cover - optional dependency
            raise ImportError(
                "google-genai package not installed. Install with: pip install google-genai"
            ) from e

        # Resolve voice name
        voice_name = type(self).resolve_voice(voice) or self.DEFAULT_VOICE

        client = genai.Client(api_key=self.api_key)
        model_id = self.model

        def _call_gemini_tts() -> bytes:
            response = client.models.generate_content(
                model=model_id,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name,
                            )
                        ),
                    ),
                ),
            )

            # Expect first candidate, first part, inline audio data
            try:
                candidate = response.candidates[0]
                part = candidate.content.parts[0]
                inline = getattr(part, "inline_data", None)
                if inline is None or inline.data is None:
                    raise ValueError("Gemini TTS response missing inline audio data")
                return inline.data
            except Exception as exc:  # pragma: no cover - defensive
                logger.error(
                    "Failed to parse Gemini TTS response",
                    extra={
                        "service": "tts",
                        "provider": "gemini_tts",
                        "model": model_id,
                        "error": str(exc),
                    },
                )
                raise

        # Run blocking client call in a background thread
        audio_bytes = await asyncio.to_thread(_call_gemini_tts)

        # Rough duration estimate based on text length and speaking rate,
        # similar to Google TTS heuristics (~150 wpm, ~5 chars/word).
        chars_per_second = 12.5 * max(speed, 0.25)
        duration_seconds = len(text) / chars_per_second if chars_per_second > 0 else 0.0
        duration_ms = int(duration_seconds * 1000)

        logger.info(
            "Gemini Flash TTS synthesis complete",
            extra={
                "service": "tts",
                "provider": "gemini_tts",
                "model": model_id,
                "voice": voice_name,
                "audio_bytes": len(audio_bytes),
                "text_length": len(text),
                "estimated_duration_ms": duration_ms,
            },
        )

        # We currently return raw audio bytes as provided by the API. The
        # format label is passed through from the caller for compatibility
        # with existing handling in the voice service.
        return TTSResult(
            audio_data=audio_bytes,
            format=format,
            duration_ms=duration_ms,
        )
