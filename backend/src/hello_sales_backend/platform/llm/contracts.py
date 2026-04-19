"""Neutral LLM substrate contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    """One normalized LLM message."""

    role: str
    content: str


class LLMCallContext(BaseModel):
    """Optional request-scoped metadata for one LLM invocation."""

    request_id: str | None = None
    trace_id: str | None = None
    actor_id: str | None = None
    timeout_seconds: float | None = Field(default=None, gt=0)
    operation: str | None = None


@dataclass(slots=True, frozen=True)
class JSONSchemaHint:
    """Provider-facing JSON schema hint."""

    name: str
    schema: dict[str, object]
    strict: bool = True


class TextGenerationResult(BaseModel):
    """Normalized text-generation result."""

    provider: str
    model: str
    output_text: str
    timeout_seconds: float | None = None


class JSONGenerationResult(BaseModel):
    """Normalized JSON-generation result."""

    provider: str
    model: str
    raw_text: str
    output_json: Any = None
    timeout_seconds: float | None = None


class LLMProviderPort(Protocol):
    """Neutral async provider contract shared by agents and workers."""

    provider_name: str

    async def generate(self, messages: list[LLMMessage]) -> TextGenerationResult: ...

    async def generate_text(
        self,
        messages: list[LLMMessage],
        *,
        context: LLMCallContext | None = None,
    ) -> TextGenerationResult: ...

    async def generate_json(
        self,
        messages: list[LLMMessage],
        *,
        schema_hint: JSONSchemaHint | None = None,
        context: LLMCallContext | None = None,
    ) -> JSONGenerationResult: ...

    def is_configured(self) -> bool: ...


# Legacy aliases preserved while the rest of the repo migrates to the neutral substrate.
ChatMessage = LLMMessage
ChatCompletion = TextGenerationResult


class ChatModelPort(Protocol):
    """Backward-compatible chat-only provider contract."""

    provider_name: str

    async def generate(self, messages: list[ChatMessage]) -> ChatCompletion: ...

    def is_configured(self) -> bool: ...
