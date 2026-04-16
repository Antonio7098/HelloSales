"""Fallback LLM provider used before a real provider is configured."""

from __future__ import annotations

from hello_sales_backend.platform.providers.llm.contracts import (
    ChatCompletion,
    ChatMessage,
    ChatModelPort,
)
from hello_sales_backend.shared.errors import app_error


class NoopChatModel(ChatModelPort):
    """Placeholder chat provider that fails explicitly when used."""

    provider_name = "noop"

    async def generate(self, messages: list[ChatMessage]) -> ChatCompletion:
        raise app_error(
            message="No LLM provider is configured for this environment",
            code="provider.llm.not_configured",
            category="provider",
            status_code=503,
            details={"provider": self.provider_name, "message_count": len(messages)},
            operation="provider.llm.generate",
            component="provider",
        )

    def is_configured(self) -> bool:
        return False
