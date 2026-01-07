"""Organization service for multi-tenant organization management - Enterprise Edition."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Organization, OrganizationMembership

logger = logging.getLogger("org")


class OrganizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert_organization(
        self,
        *,
        org_id: str,  # WorkOS organization ID
        name: str | None = None,
        user_id: UUID | None = None,
    ) -> Organization:
        """Upsert an organization by its WorkOS organization ID."""
        result = await self.db.execute(
            select(Organization).where(Organization.org_id == org_id)
        )
        org = result.scalar_one_or_none()
        if org is not None:
            if name is not None and org.name != name:
                org.name = name
            logger.info(
                "Organization upserted",
                extra={
                    "service": "org",
                    "operation": "org.upsert",
                    "status": "existing",
                    "org_id": org_id,
                    "organization_id": str(org.id),
                    "user_id": str(user_id) if user_id else None,
                },
            )
            return org

        org = Organization(org_id=org_id, name=name)

        created = False
        try:
            async with self.db.begin_nested():
                self.db.add(org)
                await self.db.flush()
                created = True
        except IntegrityError:
            result = await self.db.execute(
                select(Organization).where(Organization.org_id == org_id)
            )
            org = result.scalar_one()

        logger.info(
            "Organization upserted",
            extra={
                "service": "org",
                "operation": "org.upsert",
                "status": "created" if created else "existing",
                "org_id": org_id,
                "organization_id": str(org.id),
                "user_id": str(user_id) if user_id else None,
            },
        )
        return org

    async def ensure_membership(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        role: str | None = None,
        permissions: dict | None = None,
    ) -> OrganizationMembership:
        """Ensure user has membership in the organization."""
        membership = await self.db.get(
            OrganizationMembership,
            {"user_id": user_id, "organization_id": organization_id},
        )
        if membership is not None:
            updated = False
            if role is not None and membership.role != role:
                membership.role = role
                updated = True

            if permissions is not None and membership.permissions != permissions:
                membership.permissions = permissions
                updated = True

            if updated:
                await self.db.flush()

            logger.info(
                "Organization membership ensured",
                extra={
                    "service": "org",
                    "operation": "org.membership.ensure",
                    "status": "updated" if updated else "existing",
                    "organization_id": str(organization_id),
                    "user_id": str(user_id),
                },
            )
            return membership

        membership = OrganizationMembership(
            user_id=user_id,
            organization_id=organization_id,
            role=role,
            permissions=permissions,
        )

        created = False
        try:
            async with self.db.begin_nested():
                self.db.add(membership)
                await self.db.flush()
                created = True
        except IntegrityError:
            membership = await self.db.get(
                OrganizationMembership,
                {"user_id": user_id, "organization_id": organization_id},
            )
            if membership is None:
                raise

        logger.info(
            "Organization membership ensured",
            extra={
                "service": "org",
                "operation": "org.membership.ensure",
                "status": "created" if created else "existing",
                "organization_id": str(organization_id),
                "user_id": str(user_id),
            },
        )
        return membership
