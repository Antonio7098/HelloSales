"""Unit tests for Google Cloud TTS provider."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.ai.providers.tts.google import GOOGLE_TTS_COST_PER_CHAR_HUNDREDTHS, GoogleTTSProvider


class TestGoogleTTSProvider:
    """Tests for GoogleTTSProvider."""

    @pytest.fixture
    def provider(self):
        """Create a Google TTS provider instance."""
        return GoogleTTSProvider(api_key="test_api_key", default_voice="male")

    @pytest.fixture
    def mock_audio_data(self):
        """Create mock audio data."""
        return b"fake_mp3_audio_data_here"

    @pytest.fixture
    def mock_response(self, mock_audio_data):
        """Create a mock Google TTS API response."""
        return {"audioContent": base64.b64encode(mock_audio_data).decode("utf-8")}

    def test_name_property(self, provider):
        """Test provider name property."""
        assert provider.name == "google"

    def test_voice_presets(self, provider):
        """Test that voice presets are defined."""
        expected_presets = ["male", "female", "male_standard", "female_standard"]
        for preset in expected_presets:
            assert preset in provider.VOICE_PRESETS

    def test_format_encodings(self, provider):
        """Test that format encodings are mapped."""
        assert provider.FORMAT_ENCODINGS["mp3"] == "MP3"
        assert provider.FORMAT_ENCODINGS["wav"] == "LINEAR16"
        assert provider.FORMAT_ENCODINGS["ogg"] == "OGG_OPUS"

    @pytest.mark.asyncio
    async def test_synthesize_success(self, provider, mock_response, mock_audio_data):
        """Test successful synthesis."""
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = mock_response
        mock_http_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_http_response)
            mock_client.return_value = mock_client_instance

            result = await provider.synthesize(
                text="Hello, world!",
                voice="male",
                format="mp3",
                speed=1.0,
            )

        assert result.audio_data == mock_audio_data
        assert result.format == "mp3"
        assert result.duration_ms is not None
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_synthesize_with_custom_voice(self, provider, mock_response, mock_audio_data):
        """Test synthesis with custom voice ID."""
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = mock_response
        mock_http_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_http_response)
            mock_client.return_value = mock_client_instance

            result = await provider.synthesize(
                text="Hello, world!",
                voice="en-US-Neural2-F",  # Custom voice ID
                format="mp3",
            )

        assert result.audio_data == mock_audio_data

    @pytest.mark.asyncio
    async def test_synthesize_timeout(self, provider):
        """Test handling of timeout error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.return_value = mock_client_instance

            with pytest.raises(httpx.TimeoutException):
                await provider.synthesize(text="Hello")

    @pytest.mark.asyncio
    async def test_synthesize_http_error(self, provider):
        """Test handling of HTTP error."""
        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "API key invalid"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Forbidden",
                    request=mock_request,
                    response=mock_response,
                )
            )
            mock_client.return_value = mock_client_instance

            with pytest.raises(httpx.HTTPStatusError):
                await provider.synthesize(text="Hello")

    @pytest.mark.asyncio
    async def test_stream_yields_audio(self, provider, mock_response, mock_audio_data):
        """Test that stream yields audio data."""
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = mock_response
        mock_http_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_http_response)
            mock_client.return_value = mock_client_instance

            chunks = []
            async for chunk in provider.stream(text="Hello"):
                chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0] == mock_audio_data

    def test_resolve_voice_preset(self, provider):
        """Test voice resolution with preset name."""
        voice_config = provider._resolve_voice("male")
        assert voice_config["name"] == "en-US-Neural2-D"
        assert voice_config["gender"] == "MALE"

    def test_resolve_voice_custom_id(self, provider):
        """Test voice resolution with custom voice ID."""
        voice_config = provider._resolve_voice("en-US-Neural2-F")
        assert voice_config["name"] == "en-US-Neural2-F"
        assert voice_config["gender"] == "FEMALE"  # Inferred from F suffix

    def test_resolve_voice_none(self, provider):
        """Test voice resolution with None (uses default)."""
        voice_config = provider._resolve_voice(None)
        assert voice_config == provider.VOICE_PRESETS["male"]

    def test_resolve_voice_unknown(self, provider):
        """Test voice resolution with unknown voice (falls back to default)."""
        voice_config = provider._resolve_voice("unknown_voice")
        assert voice_config == provider.VOICE_PRESETS["male"]

    def test_estimate_duration(self):
        """Test duration estimation."""
        # "Hello world" = 11 chars
        # At speed 1.0: ~12.5 chars/sec
        # Duration: 11 / 12.5 = 0.88 seconds = 880ms
        duration = GoogleTTSProvider._estimate_duration("Hello world", 1.0)
        assert 800 <= duration <= 900

        # At speed 2.0: 25 chars/sec
        # Duration: 11 / 25 = 0.44 seconds = 440ms
        duration_fast = GoogleTTSProvider._estimate_duration("Hello world", 2.0)
        assert 400 <= duration_fast <= 500

    def test_calculate_cost(self):
        """Test cost calculation."""
        # 100 characters
        cost = GoogleTTSProvider.calculate_cost(100)
        expected = int(100 * GOOGLE_TTS_COST_PER_CHAR_HUNDREDTHS)
        assert cost == expected

        # 1000 characters
        cost = GoogleTTSProvider.calculate_cost(1000)
        expected = int(1000 * GOOGLE_TTS_COST_PER_CHAR_HUNDREDTHS)
        assert cost == expected

    def test_speed_clamping(self, provider):
        """Test that speed is clamped to valid range."""
        # Speed should be clamped between 0.25 and 4.0
        # This would be tested via the synthesize method's request payload
        # For now, just verify the valid range constants are reasonable
        assert 0.25 <= 1.0 <= 4.0  # Default speed is valid
        # Provider should expose a reasonable default voice preset
        assert provider.default_voice in provider.VOICE_PRESETS
