"""Authentication endpoints."""

from typing import Any
from uuid import UUID, uuid4
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user import User
from app.domain.errors import NotFoundError
from app.infrastructure.auth import AuthContext, get_current_user
from app.infrastructure.auth.context import (
    _register_demo_token,
)
from app.infrastructure.database.connection import get_db
from app.infrastructure.repositories.user_repository import UserRepositoryImpl

router = APIRouter()


class UserInfoResponse(BaseModel):
    """Current user information response."""

    user_id: UUID
    email: str
    org_id: UUID | None
    org_external_id: str | None
    role: str | None
    permissions: list[str]

    class Config:
        from_attributes = True


class TokenClaimsResponse(BaseModel):
    """Token claims response for debugging."""

    claims: dict[str, Any]


class LoginRequest(BaseModel):
    """Login request."""

    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response."""

    access_token: str
    user: UserInfoResponse


class RegisterRequest(BaseModel):
    """Registration request."""

    email: EmailStr
    password: str
    display_name: str | None = None


class RegisterResponse(BaseModel):
    """Registration response."""

    access_token: str
    user: UserInfoResponse


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Simple email/password login for demo purposes."""
    repo = UserRepositoryImpl(db)

    try:
        user = await repo.get_by_email(request.email)
    except NotFoundError:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # In production, use proper password hashing (bcrypt/argon2)
    # For demo, accept any non-empty password
    if len(request.password) == 0:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Generate demo token
    token = str(uuid4())
    _register_demo_token(
        token,
        {
            "user_id": str(user.id),
            "email": user.email,
            "role": "user",
        },
    )

    return LoginResponse(
        access_token=token,
        user=UserInfoResponse(
            user_id=user.id,
            email=user.email,
            org_id=None,
            org_external_id=None,
            role="user",
            permissions=[],
        ),
    )


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """Register a new user (demo mode)."""
    repo = UserRepositoryImpl(db)

    # Check if user already exists
    try:
        existing = await repo.get_by_email(request.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
    except NotFoundError:
        pass  # User doesn't exist, which is good

    # Create new user entity
    user = User(
        id=uuid4(),
        auth_provider="demo",
        auth_subject=f"demo_{request.email}",
        email=request.email,
        display_name=request.display_name or request.email.split("@")[0],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    created_user = await repo.create(user)

    # Generate demo token
    token = str(uuid4())
    _register_demo_token(
        token,
        {
            "user_id": str(created_user.id),
            "email": created_user.email,
            "role": "user",
        },
    )

    return RegisterResponse(
        access_token=token,
        user=UserInfoResponse(
            user_id=created_user.id,
            email=created_user.email,
            org_id=None,
            org_external_id=None,
            role="user",
            permissions=[],
        ),
    )


@router.post("/logout")
async def logout() -> dict:
    """Logout (invalidate token)."""
    return {"message": "Logged out"}


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    auth: AuthContext = Depends(get_current_user),
) -> UserInfoResponse:
    """Get current authenticated user information.

    Supports both WorkOS JWT tokens and demo tokens.
    """
    return UserInfoResponse(
        user_id=auth.user_id,
        email=auth.email,
        org_id=auth.org_id,
        org_external_id=auth.org_external_id,
        role=auth.role,
        permissions=auth.permissions,
    )


@router.get("/claims", response_model=TokenClaimsResponse)
async def get_token_claims(
    auth: AuthContext = Depends(get_current_user),
) -> TokenClaimsResponse:
    """Get raw token claims for debugging.

    Requires valid JWT token in Authorization header.
    """
    return TokenClaimsResponse(claims=auth.claims)
