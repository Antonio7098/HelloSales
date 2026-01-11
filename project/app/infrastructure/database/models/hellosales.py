"""Sales script and email database models."""

from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.sales_email import SalesEmail
from app.domain.entities.sales_script import SalesScript
from app.infrastructure.database.models.base import Base, TimestampMixin


class SalesScriptModel(Base, TimestampMixin):
    """SQLAlchemy model for sales_scripts table."""

    __tablename__ = "sales_scripts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Associations
    product_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    client_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Script metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    script_type: Mapped[str] = mapped_column(String(50), nullable=False, default="general")

    # Script content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    key_talking_points: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    objection_handlers: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, default=dict)
    discovery_questions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    closing_techniques: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    # Generation metadata
    generated_by_session_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    generation_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Versioning
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_script_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sales_scripts.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    organization = relationship("OrganizationModel", back_populates="sales_scripts")
    product = relationship("ProductModel", back_populates="sales_scripts")
    client = relationship("ClientModel", back_populates="sales_scripts")
    parent_script = relationship("SalesScriptModel", remote_side=[id])

    def to_entity(self) -> SalesScript:
        """Convert to domain entity."""
        return SalesScript(
            id=self.id,
            org_id=self.org_id,
            name=self.name,
            content=self.content,
            product_id=self.product_id,
            client_id=self.client_id,
            description=self.description,
            script_type=self.script_type,  # type: ignore
            key_talking_points=self.key_talking_points or [],
            objection_handlers=self.objection_handlers or {},
            discovery_questions=self.discovery_questions or [],
            closing_techniques=self.closing_techniques or [],
            generated_by_session_id=self.generated_by_session_id,
            generation_prompt=self.generation_prompt,
            model_id=self.model_id,
            version=self.version,
            parent_script_id=self.parent_script_id,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: SalesScript) -> "SalesScriptModel":
        """Create from domain entity."""
        return cls(
            id=entity.id,
            org_id=entity.org_id,
            name=entity.name,
            content=entity.content,
            product_id=entity.product_id,
            client_id=entity.client_id,
            description=entity.description,
            script_type=entity.script_type,
            key_talking_points=entity.key_talking_points,
            objection_handlers=entity.objection_handlers,
            discovery_questions=entity.discovery_questions,
            closing_techniques=entity.closing_techniques,
            generated_by_session_id=entity.generated_by_session_id,
            generation_prompt=entity.generation_prompt,
            model_id=entity.model_id,
            version=entity.version,
            parent_script_id=entity.parent_script_id,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class SalesEmailModel(Base, TimestampMixin):
    """SQLAlchemy model for sales_emails table."""

    __tablename__ = "sales_emails"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Associations
    product_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    client_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Email metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_type: Mapped[str] = mapped_column(String(50), nullable=False, default="general")

    # Email content
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    call_to_action: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Personalization hints
    personalization_fields: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    # Generation metadata
    generated_by_session_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    generation_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Versioning
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_email_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sales_emails.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    organization = relationship("OrganizationModel", back_populates="sales_emails")
    product = relationship("ProductModel", back_populates="sales_emails")
    client = relationship("ClientModel", back_populates="sales_emails")
    parent_email = relationship("SalesEmailModel", remote_side=[id])

    def to_entity(self) -> SalesEmail:
        """Convert to domain entity."""
        return SalesEmail(
            id=self.id,
            org_id=self.org_id,
            name=self.name,
            subject=self.subject,
            body=self.body,
            product_id=self.product_id,
            client_id=self.client_id,
            description=self.description,
            email_type=self.email_type,  # type: ignore
            call_to_action=self.call_to_action,
            personalization_fields=self.personalization_fields or [],
            generated_by_session_id=self.generated_by_session_id,
            generation_prompt=self.generation_prompt,
            model_id=self.model_id,
            version=self.version,
            parent_email_id=self.parent_email_id,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: SalesEmail) -> "SalesEmailModel":
        """Create from domain entity."""
        return cls(
            id=entity.id,
            org_id=entity.org_id,
            name=entity.name,
            subject=entity.subject,
            body=entity.body,
            product_id=entity.product_id,
            client_id=entity.client_id,
            description=entity.description,
            email_type=entity.email_type,
            call_to_action=entity.call_to_action,
            personalization_fields=entity.personalization_fields,
            generated_by_session_id=entity.generated_by_session_id,
            generation_prompt=entity.generation_prompt,
            model_id=entity.model_id,
            version=entity.version,
            parent_email_id=entity.parent_email_id,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
