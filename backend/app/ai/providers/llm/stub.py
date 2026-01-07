"""Stub providers for testing and development."""

import asyncio
import json
import os
from collections.abc import AsyncGenerator

from app.ai.providers.base import (
    LLMMessage,
    LLMProvider,
    LLMResponse,
    STTProvider,
    STTResult,
    TTSProvider,
    TTSResult,
)
from app.ai.providers.registry import (
    register_llm_provider,
    register_stt_provider,
    register_tts_provider,
)


def _env_str(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _env_int(name: str, default: int) -> int:
    raw = _env_str(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    raw = _env_str(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _chunk_text(text: str, chunk_size: int) -> list[str]:
    if chunk_size <= 0:
        return [text]
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


@register_llm_provider
class StubLLMProvider(LLMProvider):
    """Stub LLM provider for testing."""

    @property
    def name(self) -> str:
        return "stub"

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        _temperature: float = 0.7,
        _max_tokens: int = 1024,
        **_kwargs,
    ) -> LLMResponse:
        """Return a stub response.

        For special prompts that expect strict JSON (triage / assessment),
        return minimal well-formed JSON so downstream parsers succeed.
        """

        await asyncio.sleep(0.1)  # Simulate latency

        prompt_text = "\n".join(m.content for m in messages)
        tokens_in = sum(len(m.content.split()) for m in messages)

        # Triage-style classifier expects a single JSON object with decision/reason
        if '"decision": "assess" | "skip"' in prompt_text:
            # Try to isolate the "Latest user response" block from the triage prompt
            latest = prompt_text
            marker = "Latest user response:\n"
            idx = prompt_text.find(marker)
            if idx != -1:
                idx += len(marker)
                end = prompt_text.find("\n\n", idx)
                if end == -1:
                    end = len(prompt_text)
                latest = prompt_text[idx:end]

            latest_lc = latest.strip().lower()

            # Heuristic: questions without much substance → skip, otherwise assess
            if "?" in latest_lc and "let me try" not in latest_lc:
                decision = "skip"
            elif any(
                phrase in latest_lc
                for phrase in [
                    "i think",
                    "we should",
                    "my proposal",
                    "the solution is",
                    "here's why",
                    "i want to practice",
                    "practice my",
                    "want to practice",
                ]
            ):
                decision = "assess"
            else:
                # Fallback: treat longer utterances as attempts, very short as chatter
                decision = "assess" if len(latest_lc) > 80 else "skip"

            content = json.dumps({"decision": decision, "reason": "stub"})
            return LLMResponse(
                content=content,
                model=model or "stub-model-triage",
                tokens_in=tokens_in,
                tokens_out=len(content.split()),
                finish_reason="stop",
            )

        # Single-skill assessment prompt (new parallel approach)
        # Returns a single JSON object, not an array
        if '"skill_id": "<uuid>"' in prompt_text and '"level": <int 0-10>' in prompt_text:
            skill_id: str | None = None

            # Try single-skill format first: "Skill (JSON):\n"
            marker = "Skill (JSON):\n"
            start = prompt_text.find(marker)
            if start != -1:
                start += len(marker)
                end = prompt_text.find("\n\n", start)
                if end == -1:
                    end = len(prompt_text)
                skill_json_str = prompt_text[start:end].strip()
                try:
                    skill_payload = json.loads(skill_json_str)
                    skill_id = skill_payload.get("skill_id")
                except Exception:
                    pass

            # Fallback to old multi-skill format: "Skills (JSON):\n" (legacy)
            if not skill_id:
                marker = "Skills (JSON):\n"
                start = prompt_text.find(marker)
                if start != -1:
                    start += len(marker)
                    end = prompt_text.find("\n\n", start)
                    if end == -1:
                        end = len(prompt_text)
                    skills_json_str = prompt_text[start:end].strip()
                    try:
                        skills_payload = json.loads(skills_json_str)
                        if skills_payload and len(skills_payload) > 0:
                            skill_id = skills_payload[0].get("skill_id")
                    except Exception:
                        pass

            if not skill_id:
                skill_id = "00000000-0000-0000-0000-000000000000"

            # Return a single object (new parallel per-skill format)
            result = {
                "skill_id": skill_id,
                "level": 5,
                "confidence": 0.8,
                "summary": "Stub assessment: moderate performance.",
                "feedback": {
                    "primary_takeaway": "This is stubbed assessment feedback.",
                    "strengths": ["Stub: clear enough structure."],
                    "improvements": ["Stub: add more concrete examples."],
                    "example_quotes": [
                        {
                            "quote": "This is a stub quote.",
                            "annotation": "Illustrative only.",
                            "type": "strength",
                        }
                    ],
                    "next_level_criteria": "Stub: speak with more detail and fewer fillers.",
                },
            }

            content = json.dumps(result)
            return LLMResponse(
                content=content,
                model=model or "stub-model-assessment",
                tokens_in=tokens_in,
                tokens_out=len(content.split()),
                finish_reason="stop",
            )

        if "MetaSummaryLLMOutput" in prompt_text and "processed_session_summary_ids" in prompt_text:
            summary_id = "00000000-0000-0000-0000-000000000000"
            marker = "INPUTS:\n"
            start = prompt_text.find(marker)
            if start != -1:
                raw_inputs = prompt_text[start + len(marker) :].strip()
                try:
                    payload = json.loads(raw_inputs)
                    summary_id = str(payload.get("session_summary_id") or summary_id)
                except Exception:
                    summary_id = summary_id

            result = {
                "memory": {
                    "schema_version": 1,
                    "preferences": [],
                    "recurring_strengths": [],
                    "recurring_issues": [],
                    "exercise_archetypes": [],
                    "milestones": [],
                    "processed_session_summary_ids": [summary_id],
                },
                "summary_text": "Stub meta summary.",
            }

            content = json.dumps(result)
            return LLMResponse(
                content=content,
                model=model or "stub-model-meta-summary",
                tokens_in=tokens_in,
                tokens_out=len(content.split()),
                finish_reason="stop",
            )

        # Default non-JSON stub response (used for general chat / summary, etc.)
        # Make it obvious that the real provider is not configured so developers
        # immediately see why behavior may look off.
        content = (
            "[STUB LLM] Real LLM provider is not configured or Groq/Gemini client "
            "library/API key is missing. This is a stubbed response."
        )
        return LLMResponse(
            content=content,
            model=model or "stub-model",
            tokens_in=tokens_in,
            tokens_out=len(content.split()),
            finish_reason="stop",
        )

    async def stream(
        self,
        _messages: list[LLMMessage],
        _model: str | None = None,
        _temperature: float = 0.7,
        _max_tokens: int = 1024,
        **_kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream stub tokens."""
        forced = os.environ.get("STUB_LLM_FORCE_STREAM_TEXT")
        print(f"[DEBUG] STUB_LLM_FORCE_STREAM_TEXT = {forced}")
        if forced is not None:
            await asyncio.sleep(0.01)
            yield str(forced)
            return

        mode = (_env_str("STUB_LLM_STREAM_MODE") or "normal").lower()
        delay_ms = _env_int("STUB_LLM_STREAM_DELAY_MS", 5)
        chunk_size = _env_int("STUB_LLM_STREAM_CHUNK_SIZE", 4)

        if mode in ("malformed", "malformed_output", "malformed_json", "invalid_json"):
            stream_text = _env_str("STUB_LLM_STREAM_TEXT")
            if stream_text is None:
                stream_text = '{"assistant_message":"hi","actions":[],"artifacts":[],}'
        else:
            stream_text = _env_str("STUB_LLM_STREAM_TEXT")
            if stream_text is None:
                stream_text = "This is a stub response from the LLM."

        chunks = _chunk_text(stream_text, chunk_size)

        fail_after = _env_int("STUB_LLM_FAIL_AFTER_CHUNKS", 3)
        should_fail = mode in ("mid_stream_failure", "midstream_failure", "fail_after")

        for emitted, chunk in enumerate(chunks):
            if should_fail and emitted >= max(0, fail_after):
                raise RuntimeError("stub_llm_mid_stream_failure")
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)
            yield chunk


@register_stt_provider
class StubSTTProvider(STTProvider):
    """Stub STT provider for testing."""

    @property
    def name(self) -> str:
        return "stub"

    async def transcribe(
        self,
        audio_data: bytes,
        _format: str = "webm",
        _language: str = "en",
        **_kwargs,
    ) -> STTResult:
        """Return a stub transcription."""
        await asyncio.sleep(0.1)  # Simulate latency

        mode = (_env_str("STUB_STT_MODE") or "normal").lower()
        if mode in ("error", "timeout", "fail"):
            message = _env_str("STUB_STT_ERROR_MESSAGE") or "stub_stt_error"
            if mode == "timeout" and "timeout" not in message.lower():
                message = f"timeout: {message}"
            raise RuntimeError(message)

        if _env_str("STUB_STT_EMPTY_TRANSCRIPT") == "true":
            transcript = ""
        else:
            env_transcript = _env_str("STUB_STT_FORCE_TRANSCRIPT")
            transcript = env_transcript if env_transcript is not None else "This is a stub transcription of the audio."

        # Debug logging
        import logging
        logger = logging.getLogger("stub_stt")
        logger.info(f"[STUB_STT] Forced transcript: '{transcript}'")

        confidence = _env_float("STUB_STT_FORCE_CONFIDENCE", 0.95)
        duration_ms = _env_int("STUB_STT_FORCE_DURATION_MS", len(audio_data) // 16)

        return STTResult(
            transcript=transcript,
            confidence=confidence,
            duration_ms=duration_ms,
        )


@register_tts_provider
class StubTTSProvider(TTSProvider):
    """Stub TTS provider for testing."""

    @property
    def name(self) -> str:
        return "stub"

    async def synthesize(
        self,
        text: str,
        _voice: str | None = None,
        format: str = "mp3",
        _speed: float = 1.0,
        **_kwargs,
    ) -> TTSResult:
        """Return stub audio data."""
        await asyncio.sleep(0.1)  # Simulate latency
        # Return minimal valid audio data (silence)
        # In reality, you'd want actual silent audio bytes
        audio_bytes = _env_int("STUB_TTS_AUDIO_BYTES", 1024)
        stub_audio = b"\x00" * max(0, audio_bytes)
        return TTSResult(
            audio_data=stub_audio,
            format=format,
            duration_ms=len(text) * 50,  # Rough estimate
        )

    async def stream(
        self,
        text: str,
        voice: str | None = None,
        format: str = "mp3",
        speed: float = 1.0,
        **kwargs,
    ) -> AsyncGenerator[bytes, None]:
        mode = (_env_str("STUB_TTS_STREAM_MODE") or "chunked").lower()
        chunk_size = _env_int("STUB_TTS_STREAM_CHUNK_SIZE", 128)
        delay_ms = _env_int("STUB_TTS_STREAM_DELAY_MS", 5)
        fail_after = _env_int("STUB_TTS_FAIL_AFTER_CHUNKS", 3)
        should_fail = mode in ("mid_stream_failure", "midstream_failure", "fail_after")

        result = await self.synthesize(
            text=text, _voice=voice, format=format, _speed=speed, **kwargs
        )
        audio = result.audio_data or b""

        if chunk_size <= 0:
            chunk_size = len(audio) if audio else 1

        for emitted, i in enumerate(range(0, len(audio), chunk_size)):
            if should_fail and emitted >= max(0, fail_after):
                raise RuntimeError("stub_tts_mid_stream_failure")
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)
            yield audio[i : i + chunk_size]
