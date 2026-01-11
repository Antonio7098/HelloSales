"""Health check endpoints."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.infrastructure.database import get_db

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: str
    version: str
    environment: str
    checks: dict[str, Any]


class ReadinessResponse(BaseModel):
    """Readiness check response."""

    ready: bool
    checks: dict[str, bool]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint.

    Returns service status without checking dependencies.
    Use /ready for full readiness check.
    """
    settings = get_settings()

    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(UTC).isoformat(),
        version=settings.version,
        environment=settings.environment,
        checks={},
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check(
    db: AsyncSession = Depends(get_db),
) -> ReadinessResponse:
    """Readiness check endpoint.

    Verifies all dependencies are available:
    - Database connection
    """
    checks: dict[str, bool] = {}

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False

    ready = all(checks.values())

    return ReadinessResponse(
        ready=ready,
        checks=checks,
    )


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """Kubernetes liveness probe endpoint.

    Simple check that the service is running.
    """
    return {"status": "alive"}
