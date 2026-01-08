import httpx
import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.config import get_settings
from app.auth.workos import verify_workos_jwt, WorkOSJWTError

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
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.workos.com/user_management/authenticate",
                json={
                    "client_id": settings.workos_client_id,
                    "client_secret": settings.workos_api_key,
                    "grant_type": "authorization_code",
                    "code": request.code,
                    "code_verifier": request.code_verifier,
                },
            )

        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code")

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
async def get_me(request: Request):
    """Get current user from WorkOS JWT token."""
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "")

    # First try to verify as WorkOS JWT
    try:
        claims = await verify_workos_jwt(token)
        # Return user info from WorkOS claims
        return {
            "id": claims.get("sub"),
            "email": claims.get("email"),
            "name": claims.get("name"),
            "role": claims.get("role", "viewer"),
        }
    except WorkOSJWTError:
        pass  # Fall back to in-memory token check for demo mode

    # Fall back to in-memory token for demo
    token_data = tokens.get(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {
        "id": token_data["user_id"],
        "email": token_data["email"],
        "role": token_data["role"],
    }
