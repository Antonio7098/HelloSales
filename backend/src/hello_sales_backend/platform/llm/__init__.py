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
    ProviderToolCall,
    ProviderToolDefinition,
    TextGenerationResult,
    ToolCallCompletionResult,
)
from hello_sales_backend.platform.llm.prompts import (
    EffectivePromptRef,
    PromptMetadata,
    PromptOwnerKind,
    effective_prompt_ref,
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
    "ProviderToolCall",
    "ProviderToolDefinition",
    "EffectivePromptRef",
    "PromptMetadata",
    "PromptOwnerKind",
    "TextGenerationResult",
    "ToolCallCompletionResult",
    "effective_prompt_ref",
    "schema_hint_from_model",
]
