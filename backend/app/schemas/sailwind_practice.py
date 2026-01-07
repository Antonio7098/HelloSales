from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RepAssignmentCreate(BaseModel):
    user_id: UUID
    product_id: UUID
    client_id: UUID
    strategy_id: UUID | None = None
    min_practice_minutes: int | None = None


class RepAssignmentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    product_id: UUID
    client_id: UUID
    strategy_id: UUID | None = None
    min_practice_minutes: int | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PracticeSessionCreate(BaseModel):
    strategy_id: UUID
    rep_assignment_id: UUID | None = None


class PracticeSessionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    strategy_id: UUID
    rep_assignment_id: UUID | None = None
    chat_session_id: UUID | None = None
    status: str
    started_at: datetime
    ended_at: datetime | None = None

    class Config:
        from_attributes = True
