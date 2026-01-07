from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProductArchetypeCreate(BaseModel):
    name: str


class ProductArchetypeUpdate(BaseModel):
    name: str | None = None
    archived: bool | None = None


class ProductArchetypeResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientArchetypeCreate(BaseModel):
    name: str
    industry: str | None = None


class ClientArchetypeUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    archived: bool | None = None


class ClientArchetypeResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    industry: str | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str
    product_archetype_id: UUID | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    product_archetype_id: UUID | None = None
    archived: bool | None = None


class ProductResponse(BaseModel):
    id: UUID
    organization_id: UUID
    product_archetype_id: UUID | None = None
    name: str
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientCreate(BaseModel):
    name: str
    industry: str | None = None
    client_archetype_id: UUID | None = None


class ClientUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    client_archetype_id: UUID | None = None
    archived: bool | None = None


class ClientResponse(BaseModel):
    id: UUID
    organization_id: UUID
    client_archetype_id: UUID | None = None
    name: str
    industry: str | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StrategyUpsert(BaseModel):
    product_id: UUID
    client_id: UUID
    strategy_text: str
    status: str | None = None


class StrategyUpdate(BaseModel):
    strategy_text: str | None = None
    status: str | None = None


class StrategyResponse(BaseModel):
    id: UUID
    organization_id: UUID
    product_id: UUID
    client_id: UUID
    status: str
    strategy_text: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
