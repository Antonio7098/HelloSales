"""Eval/benchmarking models for test suites, runs, and results.

Follows the schema defined in EVL-003-benchmarking.md.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EvalTestSuite(Base):
    """Group of eval test cases.

    Represents a logical suite used for benchmarking different models/prompts.
    """

    __tablename__ = "eval_test_suites"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    test_cases: Mapped[list[EvalTestCase]] = relationship(
        "EvalTestCase",
        back_populates="suite",
        cascade="all, delete-orphan",
    )
    benchmark_runs: Mapped[list[EvalBenchmarkRun]] = relationship(
        "EvalBenchmarkRun",
        back_populates="suite",
        cascade="all, delete-orphan",
    )


class EvalTestCase(Base):
    """Individual eval test case (triage + assessment ground truth)."""

    __tablename__ = "eval_test_cases"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    suite_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("eval_test_suites.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Optional linkage to production data
    source_interaction_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("interactions.id", ondelete="CASCADE"),
        nullable=True,
    )
    source_session_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Input data
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    context_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tracked_skills: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Ground truth: triage
    expected_triage_decision: Mapped[str | None] = mapped_column(String, nullable=True)
    triage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Ground truth: assessment (per skill)
    expected_assessments: Mapped[dict[str, Any] | list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    labeled_by: Mapped[str | None] = mapped_column(String, nullable=True)
    labeled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    suite: Mapped[EvalTestSuite] = relationship(
        "EvalTestSuite",
        back_populates="test_cases",
    )
    results: Mapped[list[EvalTestResult]] = relationship(
        "EvalTestResult",
        back_populates="test_case",
        cascade="all, delete-orphan",
    )


class EvalBenchmarkRun(Base):
    """One execution of a suite against a particular model/config."""

    __tablename__ = "eval_benchmark_runs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    suite_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("eval_test_suites.id"),
        nullable=True,
    )
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    suite: Mapped[EvalTestSuite | None] = relationship(
        "EvalTestSuite",
        back_populates="benchmark_runs",
    )
    results: Mapped[list[EvalTestResult]] = relationship(
        "EvalTestResult",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class EvalTestResult(Base):
    """Per-test-case result for a benchmark run."""

    __tablename__ = "eval_test_results"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("eval_benchmark_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    test_case_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("eval_test_cases.id"),
        nullable=False,
    )

    # Triage results
    actual_triage_decision: Mapped[str | None] = mapped_column(String, nullable=True)
    triage_correct: Mapped[bool | None] = mapped_column(
        nullable=True,
    )
    triage_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Assessment results
    actual_assessments: Mapped[dict[str, Any] | list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    assessment_scores: Mapped[dict[str, Any] | list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Aggregate metrics
    overall_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_cents: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)

    raw_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    run: Mapped[EvalBenchmarkRun] = relationship(
        "EvalBenchmarkRun",
        back_populates="results",
    )
    test_case: Mapped[EvalTestCase] = relationship(
        "EvalTestCase",
        back_populates="results",
    )
