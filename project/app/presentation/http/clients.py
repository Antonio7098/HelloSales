"""Clients API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.client import Client
from app.infrastructure.auth.context import AuthContext, get_auth
from app.infrastructure.database.connection import get_db
from app.infrastructure.repositories.client_repository import ClientRepositoryImpl
from app.infrastructure.telemetry import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/clients", tags=["clients"])


# Request/Response models
class CreateClientRequest(BaseModel):
    """Request to create a client."""

    name: str = Field(..., min_length=1, max_length=255)
    company: str | None = None
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    pain_points: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    notes: str | None = None


class UpdateClientRequest(BaseModel):
    """Request to update a client."""

    name: str | None = Field(None, min_length=1, max_length=255)
    company: str | None = None
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    pain_points: list[str] | None = None
    goals: list[str] | None = None
    notes: str | None = None


class ClientResponse(BaseModel):
    """Client response."""

    id: UUID
    org_id: UUID
    name: str
    company: str | None
    title: str | None
    email: str | None
    phone: str | None
    pain_points: list[str]
    goals: list[str]
    notes: str | None
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# Endpoints
@router.post("", response_model=ClientResponse)
async def create_client(
    request: CreateClientRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth),
) -> ClientResponse:
    """Create a new client."""
    if not auth.org_id:
        raise HTTPException(status_code=400, detail="Organization required")

    from uuid import uuid4

    client = Client(
        id=uuid4(),
        org_id=auth.org_id,
        name=request.name,
        company=request.company,
        title=request.title,
        email=request.email,
        phone=request.phone,
        pain_points=request.pain_points,
        goals=request.goals,
        notes=request.notes,
    )

    repo = ClientRepositoryImpl(db)
    created = await repo.create(client)

    logger.info(
        "Client created",
        extra={"client_id": str(created.id), "org_id": str(auth.org_id)},
    )

    return _client_to_response(created)


@router.get("", response_model=list[ClientResponse])
async def list_clients(
    active_only: bool = True,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth),
) -> list[ClientResponse]:
    """List clients for the organization."""
    if not auth.org_id:
        raise HTTPException(status_code=400, detail="Organization required")

    repo = ClientRepositoryImpl(db)
    clients = await repo.list_by_org(
        auth.org_id,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )

    return [_client_to_response(c) for c in clients]


@router.get("/search", response_model=list[ClientResponse])
async def search_clients(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth),
) -> list[ClientResponse]:
    """Search clients by name or company."""
    if not auth.org_id:
        raise HTTPException(status_code=400, detail="Organization required")

    repo = ClientRepositoryImpl(db)
    clients = await repo.search(auth.org_id, q, limit=limit)

    return [_client_to_response(c) for c in clients]


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth),
) -> ClientResponse:
    """Get a client by ID."""
    if not auth.org_id:
        raise HTTPException(status_code=400, detail="Organization required")

    repo = ClientRepositoryImpl(db)
    client = await repo.get_by_id(client_id, auth.org_id)

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return _client_to_response(client)


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: UUID,
    request: UpdateClientRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth),
) -> ClientResponse:
    """Update a client."""
    if not auth.org_id:
        raise HTTPException(status_code=400, detail="Organization required")

    repo = ClientRepositoryImpl(db)
    client = await repo.get_by_id(client_id, auth.org_id)

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Update fields
    if request.name is not None:
        client.name = request.name
    if request.company is not None:
        client.company = request.company
    if request.title is not None:
        client.title = request.title
    if request.email is not None:
        client.email = request.email
    if request.phone is not None:
        client.phone = request.phone
    if request.pain_points is not None:
        client.pain_points = request.pain_points
    if request.goals is not None:
        client.goals = request.goals
    if request.notes is not None:
        client.notes = request.notes

    updated = await repo.update(client)

    logger.info(
        "Client updated",
        extra={"client_id": str(client_id), "org_id": str(auth.org_id)},
    )

    return _client_to_response(updated)


@router.delete("/{client_id}")
async def delete_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth),
) -> dict[str, bool]:
    """Delete (deactivate) a client."""
    if not auth.org_id:
        raise HTTPException(status_code=400, detail="Organization required")

    repo = ClientRepositoryImpl(db)
    deleted = await repo.delete(client_id, auth.org_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Client not found")

    logger.info(
        "Client deleted",
        extra={"client_id": str(client_id), "org_id": str(auth.org_id)},
    )

    return {"deleted": True}


def _client_to_response(client: Client) -> ClientResponse:
    """Convert client entity to response model."""
    return ClientResponse(
        id=client.id,
        org_id=client.org_id,
        name=client.name,
        company=client.company,
        title=client.title,
        email=client.email,
        phone=client.phone,
        pain_points=client.pain_points,
        goals=client.goals,
        notes=client.notes,
        is_active=client.is_active,
        created_at=client.created_at.isoformat(),
        updated_at=client.updated_at.isoformat(),
    )
