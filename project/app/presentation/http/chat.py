"""Chat API endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.pipelines.chat_pipeline import create_chat_pipeline
from app.application.services.session_service import SessionService
from app.config import Settings, get_settings
from app.domain.entities.session import Session
from app.domain.errors import SessionNotFoundError, ValidationError
from app.infrastructure.auth.context import AuthContext, get_auth
from app.infrastructure.database.connection import get_db
from app.infrastructure.telemetry import get_logger, request_id_var

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


# Request/Response models
class CreateSessionRequest(BaseModel):
    """Request to create a new chat session."""

    product_id: UUID | None = None
    client_id: UUID | None = None
    metadata: dict[str, Any] | None = None


class SessionResponse(BaseModel):
    """Chat session response."""

    id: UUID
    user_id: UUID
    org_id: UUID | None
    product_id: UUID | None
    client_id: UUID | None
    state: str
    interaction_count: int
    started_at: str
    ended_at: str | None

    class Config:
        from_attributes = True


class ChatMessageRequest(BaseModel):
    """Request to send a chat message."""

    message: str = Field(..., min_length=1, max_length=10000)
    model: str | None = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1024, ge=1, le=4096)


class ChatMessageResponse(BaseModel):
    """Chat message response."""

    session_id: UUID
    response: str
    tokens_in: int
    tokens_out: int
    blocked: bool = False
    block_reason: str | None = None


class InteractionResponse(BaseModel):
    """Chat interaction response."""

    id: UUID
    role: str
    content: str | None
    sequence_number: int
    created_at: str


# Endpoints
@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth),
) -> SessionResponse:
    """Create a new chat session."""
    service = SessionService(db)

    session = await service.create_session(
        user_id=auth.user_id,
        org_id=auth.org_id,
        product_id=request.product_id,
        client_id=request.client_id,
        metadata=request.metadata,
    )

    return _session_to_response(session)


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth),
) -> list[SessionResponse]:
    """List active chat sessions for the current user."""
    service = SessionService(db)
    sessions = await service.get_active_sessions(auth.user_id, limit=limit)
    return [_session_to_response(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth),
) -> SessionResponse:
    """Get a chat session by ID."""
    service = SessionService(db)

    try:
        session = await service.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify ownership
    if session.user_id != auth.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return _session_to_response(session)


@router.post("/sessions/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth),
) -> SessionResponse:
    """End a chat session."""
    service = SessionService(db)

    try:
        session = await service.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify ownership
    if session.user_id != auth.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        session = await service.end_session(session_id)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return _session_to_response(session)


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    session_id: UUID,
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth),
    settings: Settings = Depends(get_settings),
) -> ChatMessageResponse:
    """Send a message in a chat session."""
    service = SessionService(db)

    # Verify session exists and user has access
    try:
        session = await service.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.user_id != auth.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not session.is_active():
        raise HTTPException(status_code=400, detail="Session is not active")

    # Create and run pipeline
    pipeline = create_chat_pipeline(db, settings)

    ctx, result = await pipeline.run(
        user_input=request.message,
        session_id=session_id,
        user_id=auth.user_id,
        org_id=auth.org_id,
        request_id=request_id_var.get(),
        product_id=session.product_id,
        client_id=session.client_id,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    if not result.success and not result.should_continue:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline failed: {result.error}",
        )

    return ChatMessageResponse(
        session_id=session_id,
        response=ctx.get_final_output(),
        tokens_in=ctx.tokens_in,
        tokens_out=ctx.tokens_out,
        blocked=ctx.output_blocked,
        block_reason=ctx.output_block_reason,
    )


@router.get("/sessions/{session_id}/history", response_model=list[InteractionResponse])
async def get_history(
    session_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth),
) -> list[InteractionResponse]:
    """Get conversation history for a session."""
    service = SessionService(db)

    # Verify session exists and user has access
    try:
        session = await service.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.user_id != auth.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    interactions = await service.get_conversation_history(session_id, limit=limit)

    return [
        InteractionResponse(
            id=i.id,
            role=i.role,
            content=i.content,
            sequence_number=i.sequence_number,
            created_at=i.created_at.isoformat(),
        )
        for i in interactions
    ]


def _session_to_response(session: Session) -> SessionResponse:
    """Convert session entity to response model."""
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        org_id=session.org_id,
        product_id=session.product_id,
        client_id=session.client_id,
        state=session.state,
        interaction_count=session.interaction_count,
        started_at=session.started_at.isoformat() if session.started_at else "",
        ended_at=session.ended_at.isoformat() if session.ended_at else None,
    )
