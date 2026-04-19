"""Neutral platform-owned LLM substrate."""

from hello_sales_backend.platform.llm.contracts import (
    ChatCompletion,
    ChatMessage,
    ChatModelPort,
    JSONGenerationResult,
    JSONSchemaHint,
    LLMCallContext,
    LLMMessage,
    LLMProviderPort,
    TextGenerationResult,
)
from hello_sales_backend.platform.llm.providers import NoopLLMProvider, OpenAICompatibleLLMProvider
from hello_sales_backend.platform.llm.schema import schema_hint_from_model

__all__ = [
    "ChatCompletion",
    "ChatMessage",
    "ChatModelPort",
    "JSONGenerationResult",
    "JSONSchemaHint",
    "LLMCallContext",
    "LLMMessage",
    "LLMProviderPort",
    "NoopLLMProvider",
    "OpenAICompatibleLLMProvider",
    "TextGenerationResult",
    "schema_hint_from_model",
]
