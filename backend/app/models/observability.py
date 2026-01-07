"""Observability models for tracking and debugging."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.interaction import Interaction
    from app.models.session import Session
    from app.models.user import User


class SummaryState(Base):
    """Mutable state for tracking summary cadence per session."""

    __tablename__ = "summary_state"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    turns_since: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_cutoff_idx: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_summary_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="summary_state")

    def __repr__(self) -> str:
        return f"<SummaryState session={self.session_id} turns={self.turns_since}>"

    def increment_turns(self) -> None:
        """Increment turn counter."""
        self.turns_since += 1

    def reset_after_summary(self, cutoff_idx: int) -> None:
        """Reset state after generating a summary."""
        self.turns_since = 0
        self.last_cutoff_idx = cutoff_idx
        self.last_summary_at = datetime.utcnow()


class ProviderCall(Base):
    """Log of all external provider API calls for observability.

    This is the single source of truth for tracking all LLM, STT, and TTS calls.
    Domain tables (TriageLog, SkillAssessment, Interaction) link here via FK.
    """

    __tablename__ = "provider_calls"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Context links (all optional)
    request_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )  # Correlate multiple calls in one request
    pipeline_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    interaction_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("interactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    org_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    # Call classification
    service: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )  # 'chat', 'triage', 'assessment', 'summary', 'voice'
    operation: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )  # 'llm', 'stt', 'tts'
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # 'groq', 'deepgram', 'google', 'openai'
    model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Full I/O for eval/debugging
    prompt_messages: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )  # Full prompt array for LLM calls
    prompt_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )  # Raw text for STT input description or TTS input
    output_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )  # Raw response (LLM text, STT transcript)
    output_parsed: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )  # Structured output if applicable (parsed JSON)

    # Metrics
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audio_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)  # For STT/TTS
    cost_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Hundredths of cents

    # Status
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    # Relationships
    session: Mapped["Session | None"] = relationship("Session")
    user: Mapped["User | None"] = relationship("User")
    interaction: Mapped["Interaction | None"] = relationship(
        "Interaction",
        foreign_keys="ProviderCall.interaction_id",
        back_populates="provider_calls",
    )
    pipeline_run: Mapped["PipelineRun | None"] = relationship(
        "PipelineRun",
        foreign_keys="ProviderCall.pipeline_run_id",
    )

    def __repr__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"<ProviderCall {self.service}/{self.operation}/{self.provider} {status}>"


class PipelineRun(Base):
    """End-to-end pipeline run metrics for observability.

    Represents a single logical run of a service pipeline such as the
    voice STT → LLM → TTS flow. Aggregates external provider calls and
    internal timings (context building, TTFT, time-to-first-audio, etc.).
    """

    __tablename__ = "pipeline_runs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # High-level classification
    service: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )  # e.g. 'voice', 'chat'

    status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    # topology: the named pipeline topology (e.g., "chat_fast", "voice_accurate")
    # This encodes both service and quality mode
    topology: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    # behavior: high-level behavior label (e.g., "practice", "roleplay", "doc_edit")
    behavior: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    quality_mode: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    request_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    org_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    # Context links (all optional)
    session_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    interaction_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("interactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Links to underlying provider_calls for drill-down
    stt_provider_call_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("provider_calls.id", ondelete="SET NULL"),
        nullable=True,
    )
    llm_provider_call_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("provider_calls.id", ondelete="SET NULL"),
        nullable=True,
    )
    tts_provider_call_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("provider_calls.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Aggregate metrics
    total_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ttft_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)  # LLM start → first token
    ttfa_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )  # Pipeline start → first audio chunk
    ttfc_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )  # LLM start → first TTS-able chunk (sentence)
    tokens_per_second: Mapped[int | None] = mapped_column(
        Integer,  # Store as int (tokens/sec * 100) for precision without float column
        nullable=True,
    )  # Output generation speed (derived: tokens_out / decode_time)

    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)

    input_audio_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_audio_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tts_chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Total TTS chunks sent

    total_cost_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Status
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Detailed stage breakdown (JSON-serialisable dict)
    stages: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Additional metadata for metrics and analysis
    run_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Context snapshot metadata (key outcome - see stageflow.md §5.1)
    context_snapshot_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    # Relationships
    session: Mapped["Session | None"] = relationship("Session")
    user: Mapped["User | None"] = relationship("User")
    interaction: Mapped["Interaction | None"] = relationship("Interaction")

    events: Mapped[list["PipelineEvent"]] = relationship(
        "PipelineEvent",
        back_populates="pipeline_run",
        cascade="all, delete-orphan",
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        "Artifact",
        back_populates="pipeline_run",
        cascade="all, delete-orphan",
    )

    stt_provider_call: Mapped["ProviderCall | None"] = relationship(
        "ProviderCall",
        foreign_keys="PipelineRun.stt_provider_call_id",
    )
    llm_provider_call: Mapped["ProviderCall | None"] = relationship(
        "ProviderCall",
        foreign_keys="PipelineRun.llm_provider_call_id",
    )
    tts_provider_call: Mapped["ProviderCall | None"] = relationship(
        "ProviderCall",
        foreign_keys="PipelineRun.tts_provider_call_id",
    )

    def __repr__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"<PipelineRun {self.service} {status} {self.total_latency_ms}ms>"


class PipelineEvent(Base):
    __tablename__ = "pipeline_events"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    pipeline_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    request_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    session_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    org_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    pipeline_run: Mapped["PipelineRun"] = relationship(
        "PipelineRun",
        back_populates="events",
    )


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    pipeline_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    session_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    org_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    pipeline_run: Mapped["PipelineRun"] = relationship(
        "PipelineRun",
        back_populates="artifacts",
    )


class DeadLetterQueue(Base):
    """Dead Letter Queue for failed pipeline runs.

    Captures pipeline runs that failed and couldn't be recovered via retries.
    Allows for later inspection, debugging, and manual reprocessing.

    See stageflow.md §5.6 for specification.
    """

    __tablename__ = "dead_letter_queue"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Original pipeline run context
    pipeline_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    request_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    session_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    org_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    # Failure classification
    service: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )  # 'voice', 'chat'
    error_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )  # e.g., 'TimeoutError', 'CircuitBreakerOpenError', 'ValidationError'
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    failed_stage: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )  # Stage that failed

    # Context snapshot at failure (for debugging)
    context_snapshot: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )  # Copy of context_snapshot_metadata from pipeline_run

    # Input data at time of failure (for reprocessing)
    input_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )  # Original request data

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )  # 'pending', 'investigating', 'resolved', 'reprocessed'
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    session: Mapped["Session | None"] = relationship("Session")
    user: Mapped["User | None"] = relationship("User")
    pipeline_run: Mapped["PipelineRun | None"] = relationship(
        "PipelineRun",
        foreign_keys="DeadLetterQueue.pipeline_run_id",
    )

    def __repr__(self) -> str:
        return f"<DeadLetterQueue {self.service}/{self.error_type} ({self.status})>"
