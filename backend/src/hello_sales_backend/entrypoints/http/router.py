"""Top-level API router."""

from fastapi import APIRouter

from hello_sales_backend.entrypoints.http.routes import (
    health,
    jobs,
    sessions,
    system,
    worker_runs,
)

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(worker_runs.router, prefix="/worker-runs", tags=["worker-runs"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
