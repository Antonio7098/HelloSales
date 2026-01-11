"""Organization and membership entities."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID


@dataclass
class Organization:
    """A multi-tenant organization container."""

    id: UUID
    external_id: str  # WorkOS org ID
    name: str
    slug: str | None = None
    settings: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Organization name is required")
        if not self.external_id:
            raise ValueError("Organization external_id is required")


@dataclass
class OrganizationMembership:
    """A user's membership in an organization with role and permissions."""

    id: UUID
    user_id: UUID
    organization_id: UUID
    role: str = "member"  # 'admin', 'member', 'viewer'
    permissions: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def has_permission(self, permission: str) -> bool:
        """Check if membership grants a specific permission."""
        # Admin role has all permissions
        if self.role == "admin":
            return True
        return self.permissions.get(permission, False)

    def is_admin(self) -> bool:
        """Check if this membership is an admin role."""
        return self.role == "admin"
