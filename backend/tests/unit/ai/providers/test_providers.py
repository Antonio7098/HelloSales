"""Tests for provider abstractions."""

import pytest

from app.ai.providers.base import LLMMessage, LLMResponse, STTResult, TTSResult
from app.ai.providers.llm.stub import StubLLMProvider, StubSTTProvider, StubTTSProvider


class TestStubLLMProvider:
    """Test StubLLMProvider."""

    @pytest.mark.asyncio
    async def test_generate(self):
        """Test generate method."""
        provider = StubLLMProvider()
        messages = [LLMMessage(role="user", content="Hello")]

        response = await provider.generate(messages)

        assert isinstance(response, LLMResponse)
        assert response.content
        assert response.model == "stub-model"
        assert response.tokens_in > 0
        assert response.tokens_out > 0

    @pytest.mark.asyncio
    async def test_stream(self):
        """Test stream method."""
        provider = StubLLMProvider()
        messages = [LLMMessage(role="user", content="Hello")]

        tokens = []
        async for token in provider.stream(messages):
            tokens.append(token)

        assert len(tokens) > 0
        assert "".join(tokens)  # Should form a sentence

    def test_name(self):
        """Test provider name."""
        provider = StubLLMProvider()
        assert provider.name == "stub"


class TestStubSTTProvider:
    """Test StubSTTProvider."""

    @pytest.mark.asyncio
    async def test_transcribe(self):
        """Test transcribe method."""
        provider = StubSTTProvider()
        audio_data = b"fake audio data"

        result = await provider.transcribe(audio_data)

        assert isinstance(result, STTResult)
        assert result.transcript
        assert result.confidence is not None

    def test_name(self):
        """Test provider name."""
        provider = StubSTTProvider()
        assert provider.name == "stub"


class TestStubTTSProvider:
    """Test StubTTSProvider."""

    @pytest.mark.asyncio
    async def test_synthesize(self):
        """Test synthesize method."""
        provider = StubTTSProvider()
        text = "Hello world"

        result = await provider.synthesize(text)

        assert isinstance(result, TTSResult)
        assert result.audio_data
        assert result.format == "mp3"

    @pytest.mark.asyncio
    async def test_stream_yields_many_chunks_deterministically(self, monkeypatch):
        provider = StubTTSProvider()

        monkeypatch.setenv("STUB_TTS_AUDIO_BYTES", "1024")
        monkeypatch.setenv("STUB_TTS_STREAM_CHUNK_SIZE", "64")
        monkeypatch.setenv("STUB_TTS_STREAM_DELAY_MS", "0")
        monkeypatch.setenv("STUB_TTS_STREAM_MODE", "chunked")

        chunks: list[bytes] = []
        async for chunk in provider.stream("hello", format="mp3"):
            chunks.append(chunk)

        assert len(chunks) > 1
        assert sum(len(c) for c in chunks) == 1024
        assert all(c == b"\x00" * len(c) for c in chunks)

    @pytest.mark.asyncio
    async def test_stream_can_fail_mid_stream(self, monkeypatch):
        provider = StubTTSProvider()

        monkeypatch.setenv("STUB_TTS_AUDIO_BYTES", "1024")
        monkeypatch.setenv("STUB_TTS_STREAM_CHUNK_SIZE", "64")
        monkeypatch.setenv("STUB_TTS_STREAM_DELAY_MS", "0")
        monkeypatch.setenv("STUB_TTS_STREAM_MODE", "mid_stream_failure")
        monkeypatch.setenv("STUB_TTS_FAIL_AFTER_CHUNKS", "2")

        emitted = 0
        with pytest.raises(RuntimeError, match="stub_tts_mid_stream_failure"):
            async for _chunk in provider.stream("hello"):
                emitted += 1

        assert emitted == 2

    def test_name(self):
        """Test provider name."""
        provider = StubTTSProvider()
        assert provider.name == "stub"
