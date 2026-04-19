"""Backward-compatible LLM provider adapters."""

from hello_sales_backend.platform.llm.contracts import (
    ChatCompletion,
    ChatMessage,
    ChatModelPort,
    JSONGenerationResult,
    JSONSchemaHint,
    LLMCallContext,
    LLMProviderPort,
    TextGenerationResult,
)
from hello_sales_backend.platform.providers.llm.noop import NoopChatModel
from hello_sales_backend.platform.providers.llm.openai_compatible import OpenAICompatibleChatModel

__all__ = [
    "ChatCompletion",
    "ChatMessage",
    "ChatModelPort",
    "JSONGenerationResult",
    "JSONSchemaHint",
    "LLMCallContext",
    "LLMProviderPort",
    "NoopChatModel",
    "OpenAICompatibleChatModel",
    "TextGenerationResult",
]
