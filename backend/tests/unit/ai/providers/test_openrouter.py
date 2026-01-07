from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.providers.base import LLMMessage
from app.ai.providers.llm.openrouter import OpenRouterProvider


class _MockStreamContext:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class TestOpenRouterProvider:
    @pytest.fixture
    def provider(self):
        return OpenRouterProvider(
            api_key="test_api_key",
            http_referer="https://example.com",
            x_title="Eloquence",
        )

    def test_name_property(self, provider):
        assert provider.name == "openrouter"

    def test_resolve_model_defaults(self):
        assert OpenRouterProvider.resolve_model(None) == OpenRouterProvider.DEFAULT_MODEL
        assert OpenRouterProvider.resolve_model("") == OpenRouterProvider.DEFAULT_MODEL
        assert OpenRouterProvider.resolve_model("gpt-4o") == OpenRouterProvider.DEFAULT_MODEL

        assert OpenRouterProvider.DEFAULT_MODEL == "nvidia/nemotron-3-nano-30b-a3b:free"

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        mock_http_response = MagicMock()
        mock_http_response.raise_for_status = MagicMock()
        mock_http_response.json.return_value = {
            "id": "cmpl_test",
            "model": "openai/gpt-4o",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hello"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 3, "completion_tokens": 1},
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_http_response)
            mock_client.return_value = mock_client_instance

            resp = await provider.generate(
                [LLMMessage(role="user", content="Hi")],
                model="openai/gpt-4o",
                temperature=0.1,
                max_tokens=5,
            )

            assert resp.content == "Hello"
            assert resp.model == "openai/gpt-4o"
            assert resp.tokens_in == 3
            assert resp.tokens_out == 1
            assert resp.finish_reason == "stop"

            args, kwargs = mock_client_instance.post.call_args
            assert args[0].endswith("/chat/completions")

            headers = kwargs.get("headers")
            assert headers["Authorization"] == "Bearer test_api_key"
            assert headers["HTTP-Referer"] == "https://example.com"
            assert headers["X-Title"] == "Eloquence"

            body = kwargs.get("json")
            assert body["model"] == "openai/gpt-4o"
            assert body["temperature"] == 0.1
            assert body["max_tokens"] == 5
            assert body["messages"][0]["role"] == "user"
            assert body["messages"][0]["content"] == "Hi"

    @pytest.mark.asyncio
    async def test_stream_success(self, provider):
        async def _aiter_lines():
            yield "data: " + json.dumps(
                {"choices": [{"delta": {"content": "Hel"}, "finish_reason": None}]}
            )
            yield "data: " + json.dumps(
                {"choices": [{"delta": {"content": "lo"}, "finish_reason": None}]}
            )
            yield "data: [DONE]"

        mock_stream_response = MagicMock()
        mock_stream_response.raise_for_status = MagicMock()
        mock_stream_response.aiter_lines = _aiter_lines

        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.stream = MagicMock(
                return_value=_MockStreamContext(mock_stream_response)
            )
            mock_client.return_value = mock_client_instance

            tokens: list[str] = []
            async for token in provider.stream(
                [LLMMessage(role="user", content="Hi")],
                model="openai/gpt-4o",
                temperature=0.2,
                max_tokens=10,
            ):
                tokens.append(token)

            assert "".join(tokens) == "Hello"

            args, kwargs = mock_client_instance.stream.call_args
            assert args[0] == "POST"
            assert args[1].endswith("/chat/completions")

            body = kwargs.get("json")
            assert body["stream"] is True
            assert body["model"] == "openai/gpt-4o"

            headers = kwargs.get("headers")
            assert headers["Authorization"] == "Bearer test_api_key"
            assert headers["HTTP-Referer"] == "https://example.com"
            assert headers["X-Title"] == "Eloquence"
