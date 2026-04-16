"""LLM provider adapters."""

from hello_sales_backend.platform.providers.llm.contracts import (
    ChatCompletion,
    ChatMessage,
    ChatModelPort,
)
from hello_sales_backend.platform.providers.llm.noop import NoopChatModel
from hello_sales_backend.platform.providers.llm.openai_compatible import OpenAICompatibleChatModel

__all__ = [
    "ChatCompletion",
    "ChatMessage",
    "ChatModelPort",
    "NoopChatModel",
    "OpenAICompatibleChatModel",
]
