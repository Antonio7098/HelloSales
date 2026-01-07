import base64
import logging
import time

import httpx

from app.ai.providers.base import STTProvider, STTResult
from app.ai.providers.registry import register_stt_provider

logger = logging.getLogger("stt")


@register_stt_provider
class GoogleSTTProvider(STTProvider):
    DEFAULT_MODEL = "default"

    @classmethod
    def resolve_model(cls, model: str | None) -> str:
        m = (model or "").strip()
        if not m:
            return cls.DEFAULT_MODEL

        is_whisper = m.startswith("whisper-") or m.startswith("gpt-4o-transcribe")
        is_deepgram = m.startswith("nova-") or m == "nova" or m == "enhanced" or m == "base"

        if is_whisper or is_deepgram:
            return cls.DEFAULT_MODEL

        return m

    def __init__(
        self,
        api_key: str,
        model: str = "default",
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.base_url = "https://speech.googleapis.com/v1/speech:recognize"
        self._client: httpx.AsyncClient | None = None

        logger.info(
            "Google STT provider initialized",
            extra={
                "service": "stt",
                "provider": "google",
                "model": model,
                "api_key_present": bool(api_key),
            },
        )

    @property
    def name(self) -> str:
        return "google"

    async def transcribe(
        self,
        audio_data: bytes,
        format: str = "webm",
        language: str = "en",
    ) -> STTResult:
        start_time = time.time()

        fmt = (format or "webm").lower()
        encoding_map = {
            "webm": "WEBM_OPUS",
            "ogg": "OGG_OPUS",
            "opus": "OGG_OPUS",
            "flac": "FLAC",
            "wav": "LINEAR16",
        }
        encoding = encoding_map.get(fmt)
        if encoding is None:
            raise ValueError(f"Unsupported audio format for Google STT: {format}")

        if not language:
            language_code = "en-US"
        elif "-" in language:
            language_code = language
        else:
            language_code = f"{language}-US"

        config = {
            "encoding": encoding,
            "languageCode": language_code,
            "model": self.model or self.DEFAULT_MODEL,
            "enableWordTimeOffsets": True,
            "enableAutomaticPunctuation": True,
        }

        audio_content = base64.b64encode(audio_data).decode("ascii")

        payload = {
            "config": config,
            "audio": {"content": audio_content},
        }

        logger.debug(
            "Google transcription request",
            extra={
                "service": "stt",
                "provider": "google",
                "model": self.model,
                "format": format,
                "language": language_code,
                "audio_bytes": len(audio_data),
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
                "Google STT request timeout",
                extra={
                    "service": "stt",
                    "provider": "google",
                    "error": str(e),
                    "timeout": self.timeout,
                },
            )
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "Google STT HTTP error",
                extra={
                    "service": "stt",
                    "provider": "google",
                    "status_code": e.response.status_code,
                    "error": e.response.text,
                },
            )
            raise

        latency_ms = int((time.time() - start_time) * 1000)
        stt_result = self._parse_response(result)

        logger.info(
            "Google transcription complete",
            extra={
                "service": "stt",
                "provider": "google",
                "model": self.model,
                "latency_ms": latency_ms,
                "audio_duration_ms": stt_result.duration_ms,
                "transcript_length": len(stt_result.transcript),
                "confidence": stt_result.confidence,
            },
        )

        return stt_result

    def _parse_response(self, result: dict) -> STTResult:
        try:
            results = result.get("results", [])
            if not results:
                return STTResult(
                    transcript="",
                    confidence=0.0,
                    duration_ms=0,
                    words=None,
                )

            transcripts: list[str] = []
            all_words: list[dict] = []

            for res in results:
                alternatives = res.get("alternatives", [])
                if not alternatives:
                    continue
                best = alternatives[0]
                text = best.get("transcript", "")
                if text:
                    transcripts.append(text)
                words = best.get("words", [])
                if words:
                    all_words.extend(words)

            if not transcripts:
                return STTResult(
                    transcript="",
                    confidence=0.0,
                    duration_ms=0,
                    words=None,
                )

            transcript = " ".join(transcripts).strip()
            first_alt = results[0].get("alternatives", [{}])[0]
            confidence = first_alt.get("confidence", 0.0)

            words_out = []
            max_end_seconds = 0.0
            for w in all_words:
                start_seconds = self._parse_time_to_seconds(
                    w.get("startTime") or w.get("start_time")
                )
                end_seconds = self._parse_time_to_seconds(w.get("endTime") or w.get("end_time"))
                if end_seconds > max_end_seconds:
                    max_end_seconds = end_seconds
                words_out.append(
                    {
                        "word": w.get("word", ""),
                        "start": start_seconds,
                        "end": end_seconds,
                        "confidence": w.get("confidence", 0.0),
                    }
                )

            duration_ms: int | None = None
            if max_end_seconds > 0:
                duration_ms = int(max_end_seconds * 1000)

            return STTResult(
                transcript=transcript,
                confidence=confidence,
                duration_ms=duration_ms,
                words=words_out or None,
            )
        except (KeyError, IndexError, TypeError, ValueError) as e:
            logger.warning(
                "Error parsing Google STT response",
                extra={
                    "service": "stt",
                    "provider": "google",
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
    def _parse_time_to_seconds(value: str | None) -> float:
        if not value or not isinstance(value, str):
            return 0.0
        text = value.strip()
        if text.endswith("s"):
            text = text[:-1]
        try:
            return float(text)
        except ValueError:
            return 0.0
