from unittest.mock import AsyncMock

import pytest

from app.ai.providers.stt.groq_whisper import GroqWhisperSTTProvider
from app.ai.substrate.events.sink import EventSink, clear_event_sink, set_event_sink


@pytest.mark.asyncio
async def test_filters_thank_you_when_no_speech_signal_missing_and_duration_long():
    provider = GroqWhisperSTTProvider(api_key="test_api_key", model="whisper-large-v3")

    mock_client = AsyncMock()
    mock_client.audio.transcriptions.create = AsyncMock(
        return_value={
            "text": "Thank you.",
            "segments": [
                {
                    "end": 14.34,
                }
            ],
        }
    )
    provider._client = mock_client

    result = await provider.transcribe(audio_data=b"fake_audio", format="webm", language="en")
    assert result.transcript == ""


@pytest.mark.asyncio
async def test_does_not_filter_hello_when_no_speech_signal_missing_and_duration_short():
    provider = GroqWhisperSTTProvider(api_key="test_api_key", model="whisper-large-v3")

    mock_client = AsyncMock()
    mock_client.audio.transcriptions.create = AsyncMock(
        return_value={
            "text": "Hello.",
            "segments": [
                {
                    "end": 1.2,
                }
            ],
        }
    )
    provider._client = mock_client

    result = await provider.transcribe(audio_data=b"fake_audio", format="webm", language="en")
    assert result.transcript.strip().lower() == "hello."


@pytest.mark.asyncio
async def test_does_not_filter_um_hello_when_no_speech_prob_high():
    provider = GroqWhisperSTTProvider(api_key="test_api_key", model="whisper-large-v3")

    mock_client = AsyncMock()
    mock_client.audio.transcriptions.create = AsyncMock(
        return_value={
            "text": "Um, hello.",
            "avg_no_speech_prob": 0.9,
            "segments": [
                {
                    "end": 1.2,
                    "no_speech_prob": 0.9,
                }
            ],
        }
    )
    provider._client = mock_client

    result = await provider.transcribe(audio_data=b"fake_audio", format="webm", language="en")
    assert result.transcript.strip().lower() == "um, hello."


@pytest.mark.asyncio
async def test_does_not_filter_hi_when_avg_logprob_low_and_no_speech_prob_high():
    provider = GroqWhisperSTTProvider(api_key="test_api_key", model="whisper-large-v3")

    mock_client = AsyncMock()
    mock_client.audio.transcriptions.create = AsyncMock(
        return_value={
            "text": "Hi",
            "avg_no_speech_prob": 0.9,
            "avg_logprob": -1.0,
            "segments": [
                {
                    "end": 0.4,
                    "no_speech_prob": 0.9,
                    "avg_logprob": -1.0,
                }
            ],
        }
    )
    provider._client = mock_client

    result = await provider.transcribe(audio_data=b"fake_audio", format="webm", language="en")
    assert result.transcript.strip().lower() == "hi"


@pytest.mark.asyncio
async def test_does_not_filter_so_hello_when_no_speech_prob_high():
    provider = GroqWhisperSTTProvider(api_key="test_api_key", model="whisper-large-v3")

    mock_client = AsyncMock()
    mock_client.audio.transcriptions.create = AsyncMock(
        return_value={
            "text": "So, hello.",
            "avg_no_speech_prob": 0.9,
            "avg_logprob": -1.0,
            "segments": [
                {
                    "end": 1.2,
                    "no_speech_prob": 0.9,
                    "avg_logprob": -1.0,
                }
            ],
        }
    )
    provider._client = mock_client

    result = await provider.transcribe(audio_data=b"fake_audio", format="webm", language="en")
    assert result.transcript.strip().lower() == "so, hello."


@pytest.mark.asyncio
async def test_does_not_filter_hello_when_no_speech_prob_high():
    provider = GroqWhisperSTTProvider(api_key="test_api_key", model="whisper-large-v3")

    mock_client = AsyncMock()
    mock_client.audio.transcriptions.create = AsyncMock(
        return_value={
            "text": "Hello.",
            "avg_no_speech_prob": 0.9,
            "segments": [
                {
                    "end": 1.2,
                    "no_speech_prob": 0.9,
                }
            ],
        }
    )
    provider._client = mock_client

    result = await provider.transcribe(audio_data=b"fake_audio", format="webm", language="en")
    assert result.transcript.strip().lower() == "hello."


@pytest.mark.asyncio
async def test_filters_thank_you_when_no_speech_signal_missing_and_duration_short():
    provider = GroqWhisperSTTProvider(api_key="test_api_key", model="whisper-large-v3")

    mock_client = AsyncMock()
    mock_client.audio.transcriptions.create = AsyncMock(
        return_value={
            "text": "Thank you.",
            "segments": [
                {
                    "end": 1.2,
                }
            ],
        }
    )
    provider._client = mock_client

    result = await provider.transcribe(audio_data=b"fake_audio", format="webm", language="en")
    assert result.transcript == ""


@pytest.mark.asyncio
async def test_does_not_filter_thank_you_when_no_speech_signal_present():
    provider = GroqWhisperSTTProvider(api_key="test_api_key", model="whisper-large-v3")

    mock_client = AsyncMock()
    mock_client.audio.transcriptions.create = AsyncMock(
        return_value={
            "text": "Thank you.",
            "avg_no_speech_prob": 0.0,
            "segments": [
                {
                    "end": 14.34,
                    "no_speech_prob": 0.0,
                }
            ],
        }
    )
    provider._client = mock_client

    result = await provider.transcribe(audio_data=b"fake_audio", format="webm", language="en")
    assert result.transcript.strip().lower() == "thank you."


@pytest.mark.asyncio
async def test_emits_transcript_filtered_to_event_sink_when_set():
    class _CapturingSink(EventSink):
        def __init__(self) -> None:
            self.events: list[tuple[str, dict]] = []

        async def emit(self, *, type: str, data: dict | None) -> None:
            self.events.append((type, data or {}))

        def try_emit(self, *, type: str, data: dict | None) -> None:
            self.events.append((type, data or {}))

    sink = _CapturingSink()
    set_event_sink(sink)
    try:
        provider = GroqWhisperSTTProvider(api_key="test_api_key", model="whisper-large-v3")

        mock_client = AsyncMock()
        mock_client.audio.transcriptions.create = AsyncMock(
            return_value={
                "text": "Thank you.",
                "segments": [
                    {
                        "end": 1.2,
                    }
                ],
            }
        )
        provider._client = mock_client

        result = await provider.transcribe(audio_data=b"fake_audio", format="webm", language="en")
        assert result.transcript == ""

        assert len(sink.events) >= 1
        event_type, payload = sink.events[0]
        assert event_type == "stt.transcript_filtered"
        assert payload.get("service") == "stt"
        assert payload.get("provider") == "groq_whisper"
        assert "reason" in payload
    finally:
        clear_event_sink()
