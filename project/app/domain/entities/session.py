"""Session, summary, and summary state entities."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID


SessionState = Literal["active", "ended"]
SessionType = Literal["chat", "script_generation", "email_generation"]


@dataclass
class Session:
    """A conversation session container."""

    id: UUID
    user_id: UUID
    org_id: UUID | None = None

    # State
    state: SessionState = "active"
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    ended_at: datetime | None = None

    # Metrics (denormalized for query performance)
    interaction_count: int = 0
    total_cost_cents: int = 0
    duration_ms: int | None = None

    # Metadata
    session_type: SessionType = "chat"
    metadata: dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def is_active(self) -> bool:
        """Check if session is still active."""
        return self.state == "active"

    def end(self) -> None:
        """End the session."""
        self.state = "ended"
        self.ended_at = datetime.now(UTC)
        if self.started_at:
            self.duration_ms = int((self.ended_at - self.started_at).total_seconds() * 1000)


@dataclass
class SessionSummary:
    """Compressed context summary for a session."""

    id: UUID
    session_id: UUID
    version: int  # Incremental version number
    summary_text: str
    cutoff_sequence: int  # Messages before this are summarized
    token_count: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class SummaryState:
    """Mutable tracking state for summary cadence."""

    id: UUID
    session_id: UUID
    turns_since_summary: int = 0
    last_cutoff_sequence: int = 0
    last_summary_at: datetime | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def should_summarize(self, threshold: int) -> bool:
        """Check if it's time to create a new summary."""
        return self.turns_since_summary >= threshold

    def increment_turn(self) -> None:
        """Increment the turn counter."""
        self.turns_since_summary += 1
        self.updated_at = datetime.now(UTC)

    def reset_after_summary(self, new_cutoff: int) -> None:
        """Reset state after creating a summary."""
        self.turns_since_summary = 0
        self.last_cutoff_sequence = new_cutoff
        self.last_summary_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)
