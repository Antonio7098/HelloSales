"""Neutral LLM provider adapters."""

from hello_sales_backend.platform.llm.providers.noop import NoopLLMProvider
from hello_sales_backend.platform.llm.providers.openai_compatible import OpenAICompatibleLLMProvider

__all__ = [
    "NoopLLMProvider",
    "OpenAICompatibleLLMProvider",
]
