"""Observability database models - provider calls, pipeline runs, events, DLQ."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.models.base import Base, TimestampMixin


class ProviderCallModel(Base):
    """SQLAlchemy model for provider_calls table - tracks all external API calls."""

    __tablename__ = "provider_calls"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Classification
    service: Mapped[str] = mapped_column(String(50), nullable=False)  # 'chat', 'script', 'email'
    operation: Mapped[str] = mapped_column(String(20), nullable=False)  # 'llm', 'stt', 'tts'
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # 'groq', 'google'
    model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Correlation
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    pipeline_run_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    session_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    interaction_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("interactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    org_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Input/Output capture
    prompt_messages: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    prompt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_parsed: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Metrics
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audio_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Status
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PipelineRunModel(Base):
    """SQLAlchemy model for pipeline_runs table - end-to-end pipeline execution tracking."""

    __tablename__ = "pipeline_runs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Classification
    service: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    topology: Mapped[str | None] = mapped_column(String(50), nullable=True)
    behavior: Mapped[str | None] = mapped_column(String(50), nullable=True)
    quality_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Correlation
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    session_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    interaction_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("interactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    org_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Provider call references
    stt_provider_call_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("provider_calls.id", ondelete="SET NULL"),
        nullable=True,
    )
    llm_provider_call_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("provider_calls.id", ondelete="SET NULL"),
        nullable=True,
    )
    tts_provider_call_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("provider_calls.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Latency metrics
    total_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ttft_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Time to first token
    ttfa_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Time to first audio
    ttfc_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Time to first chunk

    # Token metrics
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_per_second: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Audio metrics
    input_audio_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_audio_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Cost
    total_cost_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Status
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Detailed breakdown
    stages: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    run_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    context_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    events = relationship("PipelineEventModel", back_populates="pipeline_run")


class PipelineEventModel(Base):
    """SQLAlchemy model for pipeline_events table - granular event stream."""

    __tablename__ = "pipeline_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    pipeline_run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Event data
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Correlation (denormalized)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    session_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    org_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

    # Timestamp
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    pipeline_run = relationship("PipelineRunModel", back_populates="events")


class DeadLetterQueueModel(Base, TimestampMixin):
    """SQLAlchemy model for dead_letter_queue table - failed pipeline recovery."""

    __tablename__ = "dead_letter_queue"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    pipeline_run_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Failure context
    error_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failed_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Request context snapshot
    context_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    input_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Correlation
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    session_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    org_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    last_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Resolution
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    resolved_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
