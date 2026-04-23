"""Backward-compatible LLM provider contracts."""

from hello_sales_backend.platform.llm.contracts import (
    ChatCompletion,
    ChatMessage,
    ChatModelPort,
    JSONGenerationResult,
    JSONSchemaHint,
    LLMCallContext,
    LLMMessage,
    LLMProviderPort,
    ProviderToolCall,
    ProviderToolDefinition,
    TextDeltaCallback,
    TextGenerationResult,
    ToolCallCompletionResult,
)

__all__ = [
    "ChatCompletion",
    "ChatMessage",
    "ChatModelPort",
    "JSONGenerationResult",
    "JSONSchemaHint",
    "LLMCallContext",
    "LLMMessage",
    "LLMProviderPort",
    "ProviderToolCall",
    "ProviderToolDefinition",
    "TextGenerationResult",
    "TextDeltaCallback",
    "ToolCallCompletionResult",
]
