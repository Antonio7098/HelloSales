"""HTTP presentation layer - REST API routes."""

from fastapi import APIRouter

from app.presentation.http.auth import router as auth_router
from app.presentation.http.chat import router as chat_router
from app.presentation.http.clients import router as clients_router
from app.presentation.http.health import router as health_router
from app.presentation.http.metrics import router as metrics_router
from app.presentation.http.products import router as products_router
from app.presentation.http.pulse import router as pulse_router

# Main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(metrics_router, tags=["Metrics"])
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(chat_router, tags=["Chat"])
api_router.include_router(products_router, tags=["Products"])
api_router.include_router(clients_router, tags=["Clients"])
api_router.include_router(pulse_router, tags=["Pulse"])

__all__ = ["api_router"]
