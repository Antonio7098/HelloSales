from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class OrganizationMeResponse(BaseModel):
    organization_id: UUID
    workos_org_id: str
    name: str | None = None


class OrganizationMembershipMeResponse(BaseModel):
    user_id: UUID
    organization_id: UUID
    role: str | None = None
    permissions: dict | None = None
    created_at: datetime
