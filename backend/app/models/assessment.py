"""Assessment-related models for skill evaluation and triage.

Matches the schema defined in ARCHITECTURE.md (Assessment Tables & TriageLog).
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.interaction import Interaction
    from app.models.observability import ProviderCall
    from app.models.session import Session
    from app.models.skill import Skill
    from app.models.user import User


class Assessment(Base):
    """Group container for one or more skill assessments.

    Each Assessment is linked to a user/session and optionally to the
    triggering Interaction. Individual per-skill results live in
    SkillAssessment rows, grouped by this Assessment.
    """

    __tablename__ = "assessments"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    interaction_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("interactions.id"),
        nullable=True,
    )
    pipeline_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id"),
        nullable=True,
    )
    group_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )
    triage_decision: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # 'skill_practice', 'general_chatter', 'manual', etc.
    triage_override_label: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # e.g. 'general_chatter_manual_assess'
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    deleted_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="assessments")
    session: Mapped["Session"] = relationship("Session", back_populates="assessments")
    interaction: Mapped["Interaction | None"] = relationship("Interaction")
    skill_assessments: Mapped[list["SkillAssessment"]] = relationship(
        "SkillAssessment",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    level_changes: Mapped[list["SkillLevelHistory"]] = relationship(
        "SkillLevelHistory",
        back_populates="source_assessment",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure id is set for test instances
        if self.id is None:
            self.id = uuid4()

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<Assessment id={self.id} session={self.session_id}>"


class SkillAssessment(Base):
    """Per-skill evaluation result for an Assessment."""

    __tablename__ = "skill_assessments"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    assessment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("skills.id"),
        nullable=False,
    )
    provider_call_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("provider_calls.id", ondelete="SET NULL"),
        nullable=True,
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
        back_populates="skill_assessments",
    )
    skill: Mapped["Skill"] = relationship("Skill")
    provider_call: Mapped["ProviderCall | None"] = relationship("ProviderCall")

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<SkillAssessment id={self.id} skill_id={self.skill_id} level={self.level}>"

    def __init__(self, **kwargs):  # type: ignore[override]
        """Allow tests to pass non-mapped metrics kwargs without touching schema.

        Tests may construct SkillAssessment(provider=..., latency_ms=..., ...).
        We pop those values off and attach them as plain attributes so they are
        available on the instance, but they are not mapped columns.
        """

        self.provider = kwargs.pop("provider", None)
        self.model_id = kwargs.pop("model_id", None)
        self.tokens_used = kwargs.pop("tokens_used", None)
        self.cost_cents = kwargs.pop("cost_cents", None)
        self.latency_ms = kwargs.pop("latency_ms", None)
        super().__init__(**kwargs)


class SkillLevelHistory(Base):
    """Audit trail for skill level changes over time."""

    __tablename__ = "skill_level_history"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("skills.id"),
        nullable=False,
    )
    from_level: Mapped[int] = mapped_column(Integer, nullable=False)
    to_level: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_assessment_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessments.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    skill: Mapped["Skill"] = relationship("Skill")
    source_assessment: Mapped["Assessment | None"] = relationship(
        "Assessment",
        back_populates="level_changes",
    )

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return (
            f"<SkillLevelHistory user_id={self.user_id} "
            f"skill_id={self.skill_id} {self.from_level}->{self.to_level}>"
        )


class TriageLog(Base):
    """Audit log of triage decisions for a session/interaction."""

    __tablename__ = "triage_log"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    interaction_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("interactions.id"),
        nullable=True,
    )
    provider_call_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("provider_calls.id", ondelete="SET NULL"),
        nullable=True,
    )
    decision: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # 'assess' | 'skip'
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    session: Mapped["Session"] = relationship("Session")
    interaction: Mapped["Interaction | None"] = relationship("Interaction")
    provider_call: Mapped["ProviderCall | None"] = relationship("ProviderCall")

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<TriageLog session={self.session_id} decision={self.decision}>"

    def __init__(self, **kwargs):  # type: ignore[override]
        """Permit latency/tokens/cost kwargs for tests without new DB columns."""

        # Pop but keep as plain attributes (not mapped)
        self.latency_ms = kwargs.pop("latency_ms", None)
        self.tokens_used = kwargs.pop("tokens_used", None)
        self.cost_cents = kwargs.pop("cost_cents", None)
        super().__init__(**kwargs)
