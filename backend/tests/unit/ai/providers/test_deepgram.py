"""Unit tests for Deepgram STT provider."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.ai.providers.stt.deepgram import DEEPGRAM_COST_PER_SECOND_HUNDREDTHS, DeepgramSTTProvider


class TestDeepgramSTTProvider:
    """Tests for DeepgramSTTProvider."""

    @pytest.fixture
    def provider(self):
        """Create a Deepgram provider instance."""
        return DeepgramSTTProvider(api_key="test_api_key", model="nova-2")

    @pytest.fixture
    def mock_response(self):
        """Create a mock Deepgram API response."""
        return {
            "metadata": {
                "duration": 3.5,
                "channels": 1,
                "model_info": {"name": "nova-2"},
            },
            "results": {
                "channels": [
                    {
                        "alternatives": [
                            {
                                "transcript": "Hello, this is a test.",
                                "confidence": 0.95,
                                "words": [
                                    {"word": "Hello", "start": 0.0, "end": 0.5, "confidence": 0.98},
                                    {"word": "this", "start": 0.6, "end": 0.8, "confidence": 0.97},
                                    {"word": "is", "start": 0.9, "end": 1.0, "confidence": 0.96},
                                    {"word": "a", "start": 1.1, "end": 1.2, "confidence": 0.99},
                                    {"word": "test", "start": 1.3, "end": 1.8, "confidence": 0.94},
                                ],
                            }
                        ]
                    }
                ]
            },
        }

    def test_name_property(self, provider):
        """Test provider name property."""
        assert provider.name == "deepgram"

    def test_format_mime_types(self, provider):
        """Test that all expected formats are mapped."""
        expected_formats = ["webm", "wav", "mp3", "m4a", "ogg", "flac", "opus"]
        for fmt in expected_formats:
            assert fmt in provider.FORMAT_MIME_TYPES

    @pytest.mark.asyncio
    async def test_transcribe_success(self, provider, mock_response):
        """Test successful transcription."""
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = mock_response
        mock_http_response.raise_for_status = MagicMock()

        provider._client = AsyncMock()
        provider._client.post = AsyncMock(return_value=mock_http_response)

        result = await provider.transcribe(
            audio_data=b"fake_audio_data",
            format="webm",
            language="en",
        )

        assert result.transcript == "Hello, this is a test."
        assert result.confidence == 0.95
        assert result.duration_ms == 3500  # 3.5 seconds * 1000
        assert result.words is not None
        assert len(result.words) == 5

    @pytest.mark.asyncio
    async def test_transcribe_empty_response(self, provider):
        """Test handling of empty response."""
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = {"results": {"channels": []}}
        mock_http_response.raise_for_status = MagicMock()

        provider._client = AsyncMock()
        provider._client.post = AsyncMock(return_value=mock_http_response)

        result = await provider.transcribe(
            audio_data=b"fake_audio_data",
            format="webm",
        )

        assert result.transcript == ""
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_transcribe_timeout(self, provider):
        """Test handling of timeout error."""
        provider._client = AsyncMock()
        provider._client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        with pytest.raises(httpx.TimeoutException):
            await provider.transcribe(
                audio_data=b"fake_audio_data",
                format="webm",
            )

    @pytest.mark.asyncio
    async def test_transcribe_http_error(self, provider):
        """Test handling of HTTP error."""
        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        provider._client = AsyncMock()
        provider._client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Unauthorized",
                request=mock_request,
                response=mock_response,
            )
        )

        with pytest.raises(httpx.HTTPStatusError):
            await provider.transcribe(
                audio_data=b"fake_audio_data",
                format="webm",
            )

    def test_calculate_cost(self):
        """Test cost calculation."""
        # 10 seconds of audio
        cost = DeepgramSTTProvider.calculate_cost(10000)
        expected = int(10 * DEEPGRAM_COST_PER_SECOND_HUNDREDTHS)
        assert cost == expected

        # 1 minute of audio
        cost = DeepgramSTTProvider.calculate_cost(60000)
        expected = int(60 * DEEPGRAM_COST_PER_SECOND_HUNDREDTHS)
        assert cost == expected

    def test_parse_response_with_words(self, provider, mock_response):
        """Test response parsing with word-level data."""
        result = provider._parse_response(mock_response, 100)

        assert result.transcript == "Hello, this is a test."
        assert result.confidence == 0.95
        assert result.duration_ms == 3500
        assert result.words is not None
        assert len(result.words) == 5
        assert result.words[0]["word"] == "Hello"
        assert result.words[0]["start"] == 0.0

    def test_parse_response_no_alternatives(self, provider):
        """Test response parsing with no alternatives."""
        response = {"results": {"channels": [{"alternatives": []}]}}
        result = provider._parse_response(response, 100)

        assert result.transcript == ""
        assert result.confidence == 0.0

    def test_parse_response_malformed(self, provider):
        """Test response parsing with malformed response."""
        response = {"unexpected": "format"}
        result = provider._parse_response(response, 100)

        assert result.transcript == ""
        assert result.confidence == 0.0
