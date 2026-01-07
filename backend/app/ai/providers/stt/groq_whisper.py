import logging
import string
import time
from typing import Any

from groq import AsyncGroq

from app.ai.providers.base import STTProvider, STTResult
from app.ai.providers.registry import register_stt_provider
from app.ai.substrate.events import get_event_sink

logger = logging.getLogger("stt")


@register_stt_provider
class GroqWhisperSTTProvider(STTProvider):
    # Whisper hallucination suppression: providing a prompt that doesn't contain
    # common hallucinated phrases helps prevent Whisper from generating them on
    # silence/noise. See: https://platform.openai.com/docs/guides/speech-to-text
    DEFAULT_MODEL = "whisper-large-v3"

    ANTI_HALLUCINATION_PROMPT = (
        "Transcribe the user's speech. If there is only silence or noise, "
        "return an empty transcript. Do not invent words or phrases. "
        "Do not add filler like 'thank you', 'thanks for watching', or acknowledgments."
    )

    # Common hallucination phrases that Whisper generates on silent/noisy audio
    # Based on research showing these are the most frequent hallucinations
    COMMON_HALLUCINATION_PHRASES = [
        "thanks for watching",
        "thank you for watching",
        "thank you very much",
        "thank you",
        "thanks",
        "subtitles by",
        "transcript",
        "i don't know",
        "i dont know",
        "hello",
        "hi",
        "hey",
        "um",
        "uh",
        "you",
        "your",
        "welcome",
        "goodbye",
        "bye",
        "see you",
        "okay",
        "ok",
        "alright",
        "sure",
        "yes",
        "no",
        "maybe",
        "well",
        "so",
        "now",
        "then",
        "and",
        "but",
        "or",
        "the",
        "a",
        "an",
    ]

    # Threshold for no_speech_prob to filter out likely hallucinations
    NO_SPEECH_PROB_THRESHOLD = 0.6

    @classmethod
    def resolve_model(cls, model: str | None) -> str:
        m = (model or "").strip()
        if not m:
            return cls.DEFAULT_MODEL

        if m.startswith("nova-") or m == "nova" or m == "enhanced" or m == "base":
            return cls.DEFAULT_MODEL

        return m

    def __init__(self, api_key: str, model: str = "whisper-large-v3"):
        self.api_key = api_key
        self.model = model
        self._client = AsyncGroq(api_key=api_key)

        logger.info(
            "Groq Whisper STT provider initialized",
            extra={
                "service": "stt",
                "provider": "groq_whisper",
                "model": model,
                "api_key_present": bool(api_key),
                "source_file": __file__,
            },
        )

    @property
    def name(self) -> str:
        return "groq_whisper"

    async def transcribe(
        self,
        audio_data: bytes,
        format: str = "webm",
        language: str = "en",
        **kwargs,
    ) -> STTResult:
        start_time = time.time()

        filename = f"audio.{format or 'webm'}"

        logger.debug(
            "Groq Whisper transcription request",
            extra={
                "service": "stt",
                "provider": "groq_whisper",
                "model": self.model,
                "format": format,
                "language": language,
                "audio_bytes": len(audio_data),
            },
        )

        try:
            response = await self._client.audio.transcriptions.create(
                file=(filename, audio_data),
                model=self.model,
                language=language,
                response_format="verbose_json",
                prompt=self.ANTI_HALLUCINATION_PROMPT,
                **kwargs,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Groq Whisper transcription failed",
                extra={
                    "service": "stt",
                    "provider": "groq_whisper",
                    "model": self.model,
                    "error": str(e),
                    "latency_ms": duration_ms,
                },
                exc_info=True,
            )
            raise

        transcription_latency_ms = int((time.time() - start_time) * 1000)

        # Parse verbose_json response
        transcript = ""
        no_speech_prob = 0.0
        avg_logprob = 0.0
        segments: list[dict[str, Any]] = []
        audio_duration_ms = 0
        max_segment_no_speech_prob = 0.0
        effective_no_speech_prob = 0.0
        no_speech_signal_available = False

        def _get_field(obj: Any, key: str, default: Any = None) -> Any:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        transcript = _get_field(response, "text", "") or ""
        original_transcript = transcript

        # Extract metadata from verbose_json response (Groq client may return a dict or a typed object)
        segments_raw = _get_field(response, "segments", []) or []
        if isinstance(segments_raw, list):
            for seg in segments_raw:
                if isinstance(seg, dict):
                    segments.append(seg)
                else:
                    segments.append(
                        {
                            "end": getattr(seg, "end", None),
                            "no_speech_prob": getattr(seg, "no_speech_prob", None),
                            "avg_logprob": getattr(seg, "avg_logprob", None),
                        }
                    )

        avg_no_speech_prob_raw = _get_field(response, "avg_no_speech_prob", None)
        no_speech_prob_raw = _get_field(response, "no_speech_prob", None)

        no_speech_signal_available = (
            avg_no_speech_prob_raw is not None
            or no_speech_prob_raw is not None
            or any(s.get("no_speech_prob") is not None for s in segments)
        )

        no_speech_prob = float(
            (avg_no_speech_prob_raw if avg_no_speech_prob_raw is not None else None)
            or (no_speech_prob_raw if no_speech_prob_raw is not None else None)
            or 0.0
        )
        avg_logprob = float(_get_field(response, "avg_logprob", 0.0) or 0.0)

        # If top-level fields aren't present, compute from segments.
        if segments:
            try:
                # Compute audio duration from the last segment end time (seconds)
                ends = [float(s.get("end", 0.0) or 0.0) for s in segments]
                audio_duration_ms = int(max(ends) * 1000) if ends else 0
            except Exception:
                audio_duration_ms = 0

            # Prefer a conservative silence signal.
            # If any segment is likely silence, treat the whole chunk cautiously.
            try:
                nsp_values = [float(s.get("no_speech_prob", 0.0) or 0.0) for s in segments]
                if nsp_values:
                    max_segment_no_speech_prob = max(nsp_values)
            except Exception:
                pass

            try:
                lp_values = [float(s.get("avg_logprob", 0.0) or 0.0) for s in segments]
                if lp_values and avg_logprob == 0.0:
                    avg_logprob = sum(lp_values) / len(lp_values)
            except Exception:
                pass

        # Always use the most conservative no-speech signal available.
        effective_no_speech_prob = max(
            float(no_speech_prob or 0.0), float(max_segment_no_speech_prob or 0.0)
        )

        normalized_for_gate = " ".join(
            transcript.lower().translate(str.maketrans("", "", string.punctuation)).split()
        )
        gate_tokens = normalized_for_gate.split() if normalized_for_gate else []
        filler_tokens = {"um", "uh", "ok", "okay", "so", "well", "now", "then"}
        first_meaningful_token = next((t for t in gate_tokens if t not in filler_tokens), "")
        is_greeting = first_meaningful_token in {"hello", "hi", "hey"}

        def _log_transcript_filtered(*, reason: str, original: str) -> None:
            payload = {
                "service": "stt",
                "provider": "groq_whisper",
                "model": self.model,
                "reason": reason,
                "original_transcript": (original or "")[:200],
                "audio_duration_ms": audio_duration_ms,
                "no_speech_prob": effective_no_speech_prob,
                "max_segment_no_speech_prob": max_segment_no_speech_prob,
                "avg_logprob": avg_logprob,
                "segments_count": len(segments),
                "no_speech_signal_available": no_speech_signal_available,
            }
            logger.info("stt.transcript_filtered", extra=payload)
            get_event_sink().try_emit(type="stt.transcript_filtered", data=payload)

        # Filter based on no_speech probability
        if effective_no_speech_prob > self.NO_SPEECH_PROB_THRESHOLD and not is_greeting:
            logger.info(
                "Groq Whisper filtered out likely hallucination",
                extra={
                    "service": "stt",
                    "provider": "groq_whisper",
                    "model": self.model,
                    "no_speech_prob": effective_no_speech_prob,
                    "max_segment_no_speech_prob": max_segment_no_speech_prob,
                    "threshold": self.NO_SPEECH_PROB_THRESHOLD,
                    "original_transcript": transcript[:100] if transcript else "",
                },
            )
            _log_transcript_filtered(reason="no_speech_prob_gate", original=transcript)
            transcript = ""
        else:
            if effective_no_speech_prob > self.NO_SPEECH_PROB_THRESHOLD and is_greeting:
                logger.info(
                    "Groq Whisper high no_speech_prob but keeping greeting",
                    extra={
                        "service": "stt",
                        "provider": "groq_whisper",
                        "model": self.model,
                        "no_speech_prob": effective_no_speech_prob,
                        "max_segment_no_speech_prob": max_segment_no_speech_prob,
                        "threshold": self.NO_SPEECH_PROB_THRESHOLD,
                        "transcript": transcript[:100] if transcript else "",
                    },
                )
            # Apply common phrase filtering for hallucinations
            transcript = self._filter_common_hallucinations(
                transcript,
                # If segments are missing, fall back to filtering these common phrases.
                silence_likely=(effective_no_speech_prob > 0.3) or (not segments),
                audio_duration_ms=audio_duration_ms,
                effective_no_speech_prob=effective_no_speech_prob,
                no_speech_signal_available=no_speech_signal_available,
            )

            # Additional filtering: if transcript is very short and avg_logprob is very negative, likely hallucination
            if (
                transcript
                and len(transcript.strip()) <= 3
                and avg_logprob < -0.5
                and not is_greeting
            ):
                logger.info(
                    "Groq Whisper filtered out short low-confidence transcript",
                    extra={
                        "service": "stt",
                        "provider": "groq_whisper",
                        "model": self.model,
                        "avg_logprob": avg_logprob,
                        "transcript_length": len(transcript),
                        "transcript": transcript,
                    },
                )
                _log_transcript_filtered(
                    reason="short_low_confidence",
                    original=original_transcript,
                )
                transcript = ""

        was_filtered = bool(original_transcript.strip()) and not bool(transcript.strip())

        logger.info(
            "Groq Whisper transcription complete",
            extra={
                "service": "stt",
                "provider": "groq_whisper",
                "model": self.model,
                "latency_ms": transcription_latency_ms,
                "transcript_length": len(transcript),
                "no_speech_prob": effective_no_speech_prob,
                "max_segment_no_speech_prob": max_segment_no_speech_prob,
                "avg_logprob": avg_logprob,
                "segments_count": len(segments),
                "filtered": was_filtered,
                "audio_duration_ms": audio_duration_ms,
            },
        )

        return STTResult(
            transcript=transcript,
            confidence=None,
            duration_ms=audio_duration_ms,
            words=None,
        )

    def _filter_common_hallucinations(
        self,
        transcript: str,
        *,
        silence_likely: bool,
        audio_duration_ms: int,
        effective_no_speech_prob: float,
        no_speech_signal_available: bool,
    ) -> str:
        """Filter out common hallucination phrases from transcript.

        This method specifically targets the most common hallucination patterns
        that Whisper generates on silent or noisy audio inputs.

        Args:
            transcript: The raw transcript from Whisper

        Returns:
            Filtered transcript with common hallucinations removed
        """
        if not transcript or not transcript.strip():
            return transcript

        # Normalize transcript for comparison
        normalized = " ".join(
            transcript.lower().translate(str.maketrans("", "", string.punctuation)).split()
        )

        normalized_tokens = normalized.split()
        filler_tokens = {"um", "uh", "ok", "okay", "so", "well", "now", "then"}
        first_meaningful_token = next(
            (t for t in normalized_tokens if t not in filler_tokens),
            "",
        )
        if first_meaningful_token in {"hello", "hi", "hey"}:
            return transcript

        always_drop_exact = {
            "thank you",
            "thanks",
            "thank you very much",
            "thanks for watching",
            "thank you for watching",
        }

        if normalized in always_drop_exact and silence_likely:
            payload = {
                "service": "stt",
                "provider": "groq_whisper",
                "model": self.model,
                "reason": "exact_common_hallucination",
                "original_transcript": (transcript or "")[:200],
                "normalized": normalized,
                "audio_duration_ms": audio_duration_ms,
                "effective_no_speech_prob": effective_no_speech_prob,
                "silence_likely": silence_likely,
                "no_speech_signal_available": no_speech_signal_available,
            }
            logger.info("stt.transcript_filtered", extra=payload)
            get_event_sink().try_emit(type="stt.transcript_filtered", data=payload)
            return ""

        # If we get a very short clip (or duration is unknown) and the transcript is one of the
        # most common Whisper-on-silence hallucinations, drop it even when no_speech_prob is low.
        # This is intentionally conservative to stop "Thank you" spam.
        short_common_hallucinations = {
            "thank you",
            "thanks",
            "thank you very much",
            "thanks for watching",
            "thank you for watching",
            "i dont know",
            "i don't know",
            "subtitles by",
            "transcript",
        }

        long_unknown_suspicious = (
            normalized in short_common_hallucinations
            and audio_duration_ms >= 8000
            and not no_speech_signal_available
        )

        if (
            normalized in short_common_hallucinations
            and (audio_duration_ms == 0 or audio_duration_ms <= 3000)
            and (
                silence_likely
                or effective_no_speech_prob >= 0.05
                or (not no_speech_signal_available)
            )
        ):
            logger.info(
                "Filtered short common hallucination",
                extra={
                    "service": "stt",
                    "provider": "groq_whisper",
                    "transcript": transcript,
                    "normalized": normalized,
                    "effective_no_speech_prob": effective_no_speech_prob,
                    "audio_duration_ms": audio_duration_ms,
                },
            )
            payload = {
                "service": "stt",
                "provider": "groq_whisper",
                "model": self.model,
                "reason": "short_common_hallucination",
                "original_transcript": (transcript or "")[:200],
                "normalized": normalized,
                "audio_duration_ms": audio_duration_ms,
                "effective_no_speech_prob": effective_no_speech_prob,
                "silence_likely": silence_likely,
                "no_speech_signal_available": no_speech_signal_available,
            }
            logger.info("stt.transcript_filtered", extra=payload)
            get_event_sink().try_emit(type="stt.transcript_filtered", data=payload)
            return ""

        if long_unknown_suspicious:
            logger.info(
                "Filtered short common hallucination",
                extra={
                    "service": "stt",
                    "provider": "groq_whisper",
                    "transcript": transcript,
                    "normalized": normalized,
                    "effective_no_speech_prob": effective_no_speech_prob,
                    "audio_duration_ms": audio_duration_ms,
                },
            )
            payload = {
                "service": "stt",
                "provider": "groq_whisper",
                "model": self.model,
                "reason": "long_unknown_suspicious",
                "original_transcript": (transcript or "")[:200],
                "normalized": normalized,
                "audio_duration_ms": audio_duration_ms,
                "effective_no_speech_prob": effective_no_speech_prob,
                "silence_likely": silence_likely,
                "no_speech_signal_available": no_speech_signal_available,
            }
            logger.info("stt.transcript_filtered", extra=payload)
            get_event_sink().try_emit(type="stt.transcript_filtered", data=payload)
            return ""

        strong_phrases = {
            "thanks for watching",
            "thank you for watching",
            "subtitles by",
            "transcript",
        }

        # Check if transcript is exactly or contains common hallucination phrases
        for phrase in self.COMMON_HALLUCINATION_PHRASES:
            phrase_norm = " ".join(
                phrase.lower().translate(str.maketrans("", "", string.punctuation)).split()
            )

            if phrase_norm in strong_phrases and (
                normalized == phrase_norm
                or normalized.startswith(phrase_norm + " ")
                or normalized.endswith(" " + phrase_norm)
                or (" " + phrase_norm + " ") in (" " + normalized + " ")
            ):
                logger.debug(
                    "Filtered common hallucination phrase",
                    extra={
                        "service": "stt",
                        "provider": "groq_whisper",
                        "phrase": phrase,
                        "transcript": transcript,
                    },
                )
                payload = {
                    "service": "stt",
                    "provider": "groq_whisper",
                    "model": self.model,
                    "reason": "strong_common_phrase",
                    "phrase": phrase,
                    "original_transcript": (transcript or "")[:200],
                    "normalized": normalized,
                    "audio_duration_ms": audio_duration_ms,
                    "effective_no_speech_prob": effective_no_speech_prob,
                    "silence_likely": silence_likely,
                    "no_speech_signal_available": no_speech_signal_available,
                }
                logger.info("stt.transcript_filtered", extra=payload)
                get_event_sink().try_emit(type="stt.transcript_filtered", data=payload)
                return ""

            # For softer/common phrases (like "thank you"), only filter when silence is likely.
            # However, if we cannot compute audio duration (0ms) we treat it as suspicious and
            # allow filtering to avoid silent hallucinations.
            is_greeting = phrase_norm in {"hello", "hi", "hey"}
            should_filter_soft = (
                silence_likely
                or audio_duration_ms == 0
                or (
                    (not no_speech_signal_available)
                    and audio_duration_ms <= 3000
                    and not is_greeting
                )
            )

            if not should_filter_soft:
                if normalized == phrase_norm:
                    logger.info(
                        "Common hallucination phrase detected but not filtered (silence not likely)",
                        extra={
                            "service": "stt",
                            "provider": "groq_whisper",
                            "phrase": phrase,
                            "transcript": transcript,
                            "effective_no_speech_prob": effective_no_speech_prob,
                            "audio_duration_ms": audio_duration_ms,
                        },
                    )
                continue

            if (
                normalized == phrase_norm
                or normalized.startswith(phrase_norm + " ")
                or normalized.endswith(" " + phrase_norm)
            ):
                logger.debug(
                    "Filtered common hallucination phrase",
                    extra={
                        "service": "stt",
                        "provider": "groq_whisper",
                        "phrase": phrase,
                        "transcript": transcript,
                    },
                )
                payload = {
                    "service": "stt",
                    "provider": "groq_whisper",
                    "model": self.model,
                    "reason": "soft_common_phrase",
                    "phrase": phrase,
                    "original_transcript": (transcript or "")[:200],
                    "normalized": normalized,
                    "audio_duration_ms": audio_duration_ms,
                    "effective_no_speech_prob": effective_no_speech_prob,
                    "silence_likely": silence_likely,
                    "no_speech_signal_available": no_speech_signal_available,
                }
                logger.info("stt.transcript_filtered", extra=payload)
                get_event_sink().try_emit(type="stt.transcript_filtered", data=payload)
                return ""

        # Check for very short transcripts that are likely filler
        if (
            silence_likely
            and len(normalized) <= 2
            and normalized in ["ok", "um", "uh", "hi", "hey", "ye", "ya"]
        ):
            logger.debug(
                "Filtered very short filler transcript",
                extra={
                    "service": "stt",
                    "provider": "groq_whisper",
                    "transcript": transcript,
                },
            )
            payload = {
                "service": "stt",
                "provider": "groq_whisper",
                "model": self.model,
                "reason": "very_short_filler",
                "original_transcript": (transcript or "")[:200],
                "normalized": normalized,
                "audio_duration_ms": audio_duration_ms,
                "effective_no_speech_prob": effective_no_speech_prob,
                "silence_likely": silence_likely,
                "no_speech_signal_available": no_speech_signal_available,
            }
            logger.info("stt.transcript_filtered", extra=payload)
            get_event_sink().try_emit(type="stt.transcript_filtered", data=payload)
            return ""

        return transcript
