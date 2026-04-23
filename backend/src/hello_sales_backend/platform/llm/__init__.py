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
    TextDeltaCallback,
    TextGenerationResult,
    ToolCallCompletionResult,
)
from hello_sales_backend.platform.llm.execution_policy import (
    LLMExecutionIssue,
    LLMExecutionIssueKind,
    LLMRetryDecision,
    decide_llm_retry,
    empty_completion_issue,
    invalid_json_issue,
    output_validation_issue,
    provider_error_issue,
    timeout_issue,
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
    "LLMExecutionIssue",
    "LLMExecutionIssueKind",
    "LLMRetryDecision",
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
    "TextDeltaCallback",
    "ToolCallCompletionResult",
    "decide_llm_retry",
    "empty_completion_issue",
    "effective_prompt_ref",
    "invalid_json_issue",
    "output_validation_issue",
    "provider_error_issue",
    "schema_hint_from_model",
    "timeout_issue",
]
