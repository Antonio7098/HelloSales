"""Operational health services."""

from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.db.session import ping_database
from hello_sales_backend.platform.workflows.runtime import WorkflowRuntime
from hello_sales_backend.shared.errors import app_error


class HealthCheckView(BaseModel):
    """Single dependency health check result."""

    status: str
    required: bool
    details: dict[str, object] = Field(default_factory=dict)


class HealthReadinessView(BaseModel):
    """Health response payload."""

    status: str
    database: str
    workflows: str
    checks: dict[str, HealthCheckView] = Field(default_factory=dict)


class HealthService:
    """Readiness and liveness checks."""

    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        workflows: WorkflowRuntime,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._workflows = workflows

    async def liveness(self) -> HealthReadinessView:
        return HealthReadinessView(
            status="live",
            database="unknown",
            workflows="ok",
            checks={
                "process": HealthCheckView(status="live", required=True),
            },
        )

    async def readiness(self) -> HealthReadinessView:
        database_status = "configured"
        workflow_status = "ok"
        overall_status = "ready"

        checks: dict[str, HealthCheckView] = {
            "database": HealthCheckView(
                status="configured",
                required=not self._settings.database_url.startswith("sqlite+aiosqlite"),
                details={"scheme": self._settings.database_url.split(":", 1)[0]},
            ),
            "workflows": HealthCheckView(
                status="ok",
                required=self._workflows.required,
                details={"engine": self._workflows.engine_name},
            ),
        }

        if not self._settings.database_url.startswith("sqlite+aiosqlite"):
            try:
                await ping_database(self._session_factory)
            except Exception as exc:
                raise app_error(
                    "Database readiness check failed",
                    code="dependency.postgres.unavailable",
                    category="dependency",
                    status_code=503,
                    severity="critical",
                    retryable=True,
                    details={"database_scheme": self._settings.database_url.split(":", 1)[0]},
                    operation="health.readiness",
                    component="db",
                    exc=exc,
                ) from exc
            database_status = "ok"
            checks["database"] = HealthCheckView(
                status=database_status,
                required=True,
                details={"scheme": self._settings.database_url.split(":", 1)[0]},
            )

        if not self._workflows.installed and self._workflows.required:
            raise app_error(
                "Required workflow runtime is unavailable",
                code="dependency.workflow_runtime.unavailable",
                category="dependency",
                status_code=503,
                severity="critical",
                details={"engine": self._workflows.engine_name},
                operation="health.readiness",
                component="workflow",
            )
        if not self._workflows.installed:
            workflow_status = "missing"
            overall_status = "degraded"
            checks["workflows"] = HealthCheckView(
                status=workflow_status,
                required=False,
                details={"engine": self._workflows.engine_name},
            )

        return HealthReadinessView(
            status=overall_status,
            database=database_status,
            workflows=workflow_status,
            checks=checks,
        )
