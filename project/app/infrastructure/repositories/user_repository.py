"""User repository implementation."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user import User
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.repositories.base import BaseRepository


class UserRepositoryImpl(BaseRepository[UserModel, User]):
    """SQLAlchemy implementation of UserRepository."""

    model_class = UserModel

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        return await super().get_by_id(user_id)

    async def get_by_auth_subject(self, auth_subject: str) -> User | None:
        """Get user by auth provider subject (WorkOS user ID)."""
        stmt = select(UserModel).where(UserModel.auth_subject == auth_subject)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return model.to_entity()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return model.to_entity()

    async def create(self, user: User) -> User:
        """Create a new user."""
        return await super().create(user)

    async def update(self, user: User) -> User:
        """Update an existing user."""
        return await super().update(user)

    async def get_or_create_by_auth_subject(
        self,
        auth_subject: str,
        email: str,
        auth_provider: str = "workos",
        display_name: str | None = None,
        avatar_url: str | None = None,
    ) -> tuple[User, bool]:
        """Get existing user or create new one.

        Returns:
            Tuple of (user, created) where created is True if new user was created.
        """
        existing = await self.get_by_auth_subject(auth_subject)
        if existing:
            return existing, False

        from uuid import uuid4
        from datetime import UTC, datetime

        user = User(
            id=uuid4(),
            auth_provider=auth_provider,
            auth_subject=auth_subject,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        created_user = await self.create(user)
        return created_user, True
