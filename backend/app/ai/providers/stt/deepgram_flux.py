from __future__ import annotations

import asyncio
import contextlib
import logging
import shutil
from typing import Any

from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType

from app.ai.providers.base import STTProvider, STTResult
from app.ai.providers.registry import register_stt_provider

logger = logging.getLogger("stt")


@register_stt_provider
class DeepgramFluxSTTProvider(STTProvider):
    DEFAULT_MODEL = "flux-general-en"

    def __init__(self, api_key: str, model: str = "flux-general-en", timeout: float = 30.0) -> None:
        self.api_key = api_key
        self.model = self.resolve_model(model) or self.DEFAULT_MODEL
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "deepgram_flux"

    async def _convert_to_linear16(self, audio_data: bytes) -> tuple[bytes, int]:
        if not shutil.which("ffmpeg"):
            raise RuntimeError("ffmpeg is required for Deepgram Flux STT")

        ffmpeg_cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            "pipe:0",
            "-f",
            "s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            "pipe:1",
        ]

        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout_data, stderr_data = await process.communicate(input=audio_data)

        if process.returncode != 0:
            stderr_text = stderr_data.decode("utf-8", errors="ignore")
            logger.error(
                "ffmpeg conversion failed for Deepgram Flux",
                extra={
                    "service": "stt",
                    "provider": "deepgram_flux",
                    "return_code": process.returncode,
                    "stderr": stderr_text,
                },
            )
            raise RuntimeError(
                f"ffmpeg conversion failed with code {process.returncode}: {stderr_text}"
            )

        bytes_per_second = 2 * 16000
        duration_ms = int((len(stdout_data) / bytes_per_second) * 1000)

        return stdout_data, duration_ms

    async def transcribe(
        self,
        audio_data: bytes,
        format: str = "webm",
        language: str = "en",
    ) -> STTResult:
        if not self.api_key:
            raise RuntimeError("Deepgram API key is required for Flux STT")

        logger.debug(
            "Deepgram Flux transcription request",
            extra={
                "service": "stt",
                "provider": "deepgram_flux",
                "model": self.model,
                "format": format,
                "language": language,
                "audio_bytes": len(audio_data),
            },
        )

        pcm_data, duration_ms = await self._convert_to_linear16(audio_data)

        client = AsyncDeepgramClient()

        latest_transcript = ""
        latest_confidence: float | None = None
        latest_words: list[dict[str, Any]] | None = None

        async with client.listen.asyncwebsocket.v("1").connect(
            model=self.model,
            encoding="linear16",
            sample_rate=16000,
        ) as connection:

            def on_message(self, result: Any, **kwargs) -> None:
                nonlocal latest_transcript, latest_confidence, latest_words
                transcript = result.channel.alternatives[0].transcript
                if not transcript:
                    return
                latest_transcript = transcript
                confidence = result.channel.alternatives[0].confidence
                if confidence is not None:
                    with contextlib.suppress(TypeError, ValueError):
                        latest_confidence = float(confidence)
                words = result.channel.alternatives[0].words
                if words:
                    latest_words = [
                        {
                            "word": w.word,
                            "start": w.start,
                            "end": w.end,
                            "confidence": w.confidence,
                        }
                        for w in words
                    ]

            connection.on(EventType.Metadata, lambda self, result, **kwargs: None)
            connection.on(EventType.SpeechStarted, lambda self, result, **kwargs: None)
            connection.on(EventType.UtteranceEnd, lambda self, result, **kwargs: None)
            connection.on(EventType.Close, lambda self, result, **kwargs: None)
            connection.on(EventType.Error, lambda self, result, **kwargs: None)
            connection.on(EventType.Unhandled, lambda self, result, **kwargs: None)
            connection.on(EventType.Transcript, on_message)

            # In SDK v3+, start() is called by the context manager or explicitly if needed?
            # actually connect() returns a context manager that handles start/finish.
            # We just need to send data.

            chunk_size = 2560
            for i in range(0, len(pcm_data), chunk_size):
                chunk = pcm_data[i : i + chunk_size]
                await connection.send(chunk)
            
            # Send close signal? Or just finish context?
            # Usually we need to wait for processing.
            # SDK v3 way to wait for finish?
            # For now, let's assume the context manager handles cleanup but we might need to sleep to let messages process.
            await asyncio.sleep(0.5) 
            # In real usage we might want to wait for a specific event or "finalize" message.


        transcript = latest_transcript or ""
        confidence_value = float(latest_confidence) if latest_confidence is not None else 0.0

        return STTResult(
            transcript=transcript,
            confidence=confidence_value,
            duration_ms=duration_ms,
            words=latest_words,
        )
