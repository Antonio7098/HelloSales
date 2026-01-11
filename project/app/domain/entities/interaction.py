"""Interaction entity - individual messages in a session."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID


Role = Literal["user", "assistant", "system"]
InputType = Literal["text", "voice"]


@dataclass
class Interaction:
    """An individual message/interaction within a session."""

    id: UUID
    session_id: UUID
    role: Role
    sequence_number: int

    # Content
    content: str | None = None
    input_type: InputType = "text"
    transcript: str | None = None  # Original transcript if voice

    # Audio (if voice)
    audio_url: str | None = None
    audio_duration_ms: int | None = None

    # Provider call references for tracing
    llm_provider_call_id: UUID | None = None
    stt_provider_call_id: UUID | None = None
    tts_provider_call_id: UUID | None = None

    # Client-generated for deduplication
    message_id: str | None = None

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def is_user_message(self) -> bool:
        """Check if this is a user message."""
        return self.role == "user"

    def is_assistant_message(self) -> bool:
        """Check if this is an assistant message."""
        return self.role == "assistant"

    def to_llm_message(self) -> dict[str, str]:
        """Convert to format suitable for LLM API calls."""
        return {
            "role": self.role,
            "content": self.content or "",
        }
