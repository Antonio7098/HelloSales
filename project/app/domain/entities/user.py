"""User entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


@dataclass
class User:
    """A user in the system, authenticated via WorkOS."""

    id: UUID
    auth_provider: str
    auth_subject: str  # WorkOS user ID
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.email:
            raise ValueError("User email is required")
        if not self.auth_subject:
            raise ValueError("User auth_subject is required")
