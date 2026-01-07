from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.interaction import Interaction


class TriageDataset(Base):
    __tablename__ = "triage_datasets"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    annotations: Mapped[list[TriageAnnotation]] = relationship(
        "TriageAnnotation",
        back_populates="dataset",
        cascade="all, delete-orphan",
    )


class TriageAnnotation(Base):
    __tablename__ = "triage_annotations"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id", "interaction_id", name="uq_triage_annotations_dataset_interaction"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    dataset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("triage_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    interaction_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("interactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    expected_decision: Mapped[str] = mapped_column(String(50), nullable=False)

    context_n: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    context_messages: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    labeled_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

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

    dataset: Mapped[TriageDataset] = relationship("TriageDataset", back_populates="annotations")
    interaction: Mapped[Interaction] = relationship("Interaction")
