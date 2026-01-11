import httpx
import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.auth.workos import verify_workos_jwt, WorkOSJWTError
from app.api.http.dependencies import get_current_user, get_identity_claims
from app.database import get_session
from app.models import User, OrganizationMembership, Organization

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    user: dict


class ExchangeCodeRequest(BaseModel):
    code: str
    code_verifier: str
    redirect_uri: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None


# Simple in-memory token storage for demo mode
tokens = {}


@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Simple email/password login for demo"""
    from app.api.http.users.router import users_db

    # Find user by email
    user = None
    for u in users_db.values():
        if u["email"] == request.email:
            user = u
            break

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # In production, use proper password hashing
    # For demo, accept password that matches "hashed_{password}"
    expected_hash = f"hashed_{request.password}"
    if user["password_hash"] != expected_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Generate token
    token = str(uuid4())
    tokens[token] = {
        "user_id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "created_at": datetime.datetime.utcnow().isoformat(),
    }

    return LoginResponse(
        access_token=token,
        user={
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
        }
    )


@router.post("/auth/workos/exchange", response_model=TokenResponse)
async def exchange_workos_code(
    request: ExchangeCodeRequest,
    settings=Depends(get_settings),
):
    """Exchange WorkOS authorization code for access token."""
    if not settings.workos_auth_enabled:
        raise HTTPException(status_code=400, detail="WorkOS auth is disabled")

    if not settings.workos_client_id or not settings.workos_api_key:
        raise HTTPException(status_code=400, detail="WorkOS is not configured")

    try:
        payload = {
            "client_id": settings.workos_client_id,
            "client_secret": settings.workos_api_key,
            "grant_type": "authorization_code",
            "code": request.code,
            "code_verifier": request.code_verifier,
        }
        
        if request.redirect_uri:
            payload["redirect_uri"] = request.redirect_uri

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.workos.com/user_management/authenticate",
                json=payload,
            )

        if response.status_code != 200:
            error_detail = response.text
            print(f"WorkOS Error: {error_detail}")  # Simple logging
            try:
                error_json = response.json()
                error_detail = error_json.get("message") or error_json.get("error_description") or response.text
            except Exception:
                pass
            raise HTTPException(status_code=400, detail=f"Failed to exchange code: {error_detail}")

        data = response.json()
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Exchange failed: {str(e)}")


@router.post("/auth/logout")
async def logout():
    """Logout (invalidate token)"""
    return {"message": "Logged out"}


@router.get("/auth/me")
async def get_me(
    user: User = Depends(get_current_user),
    identity=Depends(get_identity_claims),
    session: AsyncSession = Depends(get_session),
):
    """Get current user from WorkOS JWT token."""
    # Find membership for the current org
    membership = None
    if identity.org_id:
        # User is already synced by get_current_user
        # We just need to find the correct membership to return the role
        stmt = select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == (
                select(Organization.id).where(Organization.org_id == str(identity.org_id))
            ).scalar_subquery()
        )
        result = await session.execute(stmt)
        membership = result.scalar_one_or_none()

    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.display_name,
        "role": (membership.role if membership and membership.role else "viewer"),
        "org_id": str(identity.org_id) if identity.org_id else None,
    }
