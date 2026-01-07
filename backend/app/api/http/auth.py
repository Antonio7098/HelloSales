import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter()


class ExchangeCodeRequest(BaseModel):
    code: str
    code_verifier: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None


@router.post("/auth/workos/exchange", response_model=TokenResponse)
async def exchange_workos_code(
    request: ExchangeCodeRequest,
    settings=Depends(get_settings),
):
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
                    "client_secret": settings.workos_api_key,  # API key as secret
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Exchange failed: {str(e)}")
