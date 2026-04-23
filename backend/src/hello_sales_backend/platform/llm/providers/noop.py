"""No-op neutral LLM provider."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from hello_sales_backend.platform.llm.contracts import (
    JSONGenerationResult,
    JSONSchemaHint,
    LLMCallContext,
    LLMMessage,
    ProviderToolDefinition,
    TextGenerationResult,
    ToolCallCompletionResult,
)
from hello_sales_backend.shared.errors import app_error


class NoopLLMProvider:
    """Placeholder provider used when no real provider is configured."""

    provider_name = "noop"

    async def generate_text(
        self,
        messages: list[LLMMessage],
        *,
        context: LLMCallContext | None = None,
    ) -> TextGenerationResult:
        raise app_error(
            message="No LLM provider is configured for this environment",
            code="provider.llm.not_configured",
            category="provider",
            status_code=503,
            details={
                "provider": self.provider_name,
                "message_count": len(messages),
                "operation": context.operation if context else None,
            },
            operation="provider.llm.generate_text",
            component="provider",
        )

    async def generate_json(
        self,
        messages: list[LLMMessage],
        *,
        schema_hint: JSONSchemaHint | None = None,
        context: LLMCallContext | None = None,
    ) -> JSONGenerationResult:
        raise app_error(
            message="No LLM provider is configured for this environment",
            code="provider.llm.not_configured",
            category="provider",
            status_code=503,
            details={
                "provider": self.provider_name,
                "message_count": len(messages),
                "schema_name": schema_hint.name if schema_hint is not None else None,
                "operation": context.operation if context else None,
            },
            operation="provider.llm.generate_json",
            component="provider",
        )

    async def generate(self, messages: list[LLMMessage]) -> TextGenerationResult:
        """Backward-compatible chat-only entrypoint."""

        return await self.generate_text(messages)

    async def complete_with_tools(
        self,
        messages: list[dict[str, object]],
        *,
        tools: list[ProviderToolDefinition],
        context: LLMCallContext | None = None,
        tool_choice: str | None = None,
        on_text_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> ToolCallCompletionResult:
        del tools, tool_choice, on_text_delta
        raise app_error(
            message="No LLM provider is configured for this environment",
            code="provider.llm.not_configured",
            category="provider",
            status_code=503,
            details={
                "provider": self.provider_name,
                "message_count": len(messages),
                "operation": context.operation if context else None,
            },
            operation="provider.llm.complete_with_tools",
            component="provider",
        )

    def is_configured(self) -> bool:
        return False
