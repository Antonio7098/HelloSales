"""LLM provider contracts."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Single chat message."""

    role: str
    content: str


class ChatCompletion(BaseModel):
    """Normalized chat completion result."""

    provider: str
    model: str
    output_text: str


class ChatModelPort(Protocol):
    """Minimal async chat model contract."""

    provider_name: str

    async def generate(self, messages: list[ChatMessage]) -> ChatCompletion: ...

    def is_configured(self) -> bool: ...
