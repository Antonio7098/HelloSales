"""Backward-compatible OpenAI-compatible provider shim."""

from hello_sales_backend.platform.llm.providers.openai_compatible import (
    OpenAICompatibleLLMProvider as OpenAICompatibleChatModel,
)

__all__ = ["OpenAICompatibleChatModel"]
