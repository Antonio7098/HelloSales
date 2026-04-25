"""Operational health services."""

from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.db.session import ping_database
from hello_sales_backend.platform.observability.runtime import ObservabilityRuntime
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
        observability: ObservabilityRuntime,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._workflows = workflows
        self._observability = observability

    async def liveness(self) -> HealthReadinessView:
        payload = HealthReadinessView(
            status="live",
            database="unknown",
            workflows="ok",
            checks={
                "process": HealthCheckView(status="live", required=True),
            },
        )
        self._record_metrics(kind="liveness", payload=payload)
        return payload

    async def readiness(self) -> HealthReadinessView:
        database_scheme = self._settings.database_url.split(":", 1)[0]
        database_required = not self._settings.database_url.startswith("sqlite+aiosqlite")
        database_status = "configured"
        workflow_status = "ok"
        overall_status = "ready"

        checks: dict[str, HealthCheckView] = {
            "database": HealthCheckView(
                status="configured",
                required=database_required,
                details={"scheme": database_scheme},
            ),
            "workflows": HealthCheckView(
                status="ok",
                required=self._workflows.required,
                details={"engine": self._workflows.engine_name},
            ),
            "web_search": HealthCheckView(
                status="disabled",
                required=self._settings.web_search_required,
                details={"provider": self._settings.resolved_web_search_provider or "noop"},
            ),
            "voice_stt": HealthCheckView(
                status="disabled",
                required=self._settings.voice_required,
                details={"provider": self._settings.voice_stt_provider or "noop"},
            ),
            "voice_tts": HealthCheckView(
                status="disabled",
                required=self._settings.voice_required,
                details={"provider": self._settings.voice_tts_provider or "noop"},
            ),
            "voice_turn_detection": HealthCheckView(
                status="disabled",
                required=self._settings.voice_required,
                details={"provider": self._settings.voice_turn_detection_provider or "noop"},
            ),
        }
        if self._settings.resolved_web_search_provider:
            if self._settings.resolved_web_search_api_key:
                checks["web_search"] = HealthCheckView(
                    status="configured",
                    required=self._settings.web_search_required,
                    details={"provider": self._settings.resolved_web_search_provider},
                )
            elif self._settings.web_search_required:
                checks["web_search"] = HealthCheckView(
                    status="not_ready",
                    required=True,
                    details={"provider": self._settings.resolved_web_search_provider},
                )
                self._record_metrics(
                    kind="readiness",
                    payload=HealthReadinessView(
                        status="not_ready",
                        database=database_status,
                        workflows=workflow_status,
                        checks=checks,
                    ),
                )
                raise app_error(
                    "Required web search provider is not configured",
                    code="dependency.web_search.not_configured",
                    category="dependency",
                    status_code=503,
                    severity="critical",
                    details={"provider": self._settings.resolved_web_search_provider},
                    operation="health.readiness",
                    component="provider",
                )
            else:
                overall_status = "degraded"
                checks["web_search"] = HealthCheckView(
                    status="missing_credentials",
                    required=False,
                    details={"provider": self._settings.resolved_web_search_provider},
                )

        voice_checks = {
            "voice_stt": self._settings.voice_stt_provider,
            "voice_tts": self._settings.voice_tts_provider,
            "voice_turn_detection": self._settings.voice_turn_detection_provider,
        }
        for check_name, provider_name in voice_checks.items():
            if provider_name == "fake":
                checks[check_name] = HealthCheckView(
                    status="configured",
                    required=self._settings.voice_required,
                    details={"provider": provider_name},
                )
            elif self._settings.voice_required:
                checks[check_name] = HealthCheckView(
                    status="not_ready",
                    required=True,
                    details={"provider": provider_name or "noop"},
                )
                self._record_metrics(
                    kind="readiness",
                    payload=HealthReadinessView(
                        status="not_ready",
                        database=database_status,
                        workflows=workflow_status,
                        checks=checks,
                    ),
                )
                raise app_error(
                    "Required voice provider is not configured",
                    code=f"dependency.{check_name}.not_configured",
                    category="dependency",
                    status_code=503,
                    severity="critical",
                    details={"provider": provider_name or "noop", "check": check_name},
                    operation="health.readiness",
                    component="provider",
                )
            elif provider_name:
                overall_status = "degraded"
                checks[check_name] = HealthCheckView(
                    status="missing_credentials",
                    required=False,
                    details={"provider": provider_name},
                )

        if database_required:
            try:
                await ping_database(self._session_factory)
            except Exception as exc:
                checks["database"] = HealthCheckView(
                    status="not_ready",
                    required=True,
                    details={"scheme": database_scheme},
                )
                self._record_metrics(
                    kind="readiness",
                    payload=HealthReadinessView(
                        status="not_ready",
                        database="not_ready",
                        workflows=workflow_status,
                        checks=checks,
                    ),
                )
                raise app_error(
                    "Database readiness check failed",
                    code="dependency.postgres.unavailable",
                    category="dependency",
                    status_code=503,
                    severity="critical",
                    retryable=True,
                    details={"database_scheme": database_scheme},
                    operation="health.readiness",
                    component="db",
                    exc=exc,
                ) from exc
            database_status = "ok"
            checks["database"] = HealthCheckView(
                status=database_status,
                required=True,
                details={"scheme": database_scheme},
            )

        if not self._workflows.installed and self._workflows.required:
            checks["workflows"] = HealthCheckView(
                status="not_ready",
                required=True,
                details={"engine": self._workflows.engine_name},
            )
            self._record_metrics(
                kind="readiness",
                payload=HealthReadinessView(
                    status="not_ready",
                    database=database_status,
                    workflows="not_ready",
                    checks=checks,
                ),
            )
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

        payload = HealthReadinessView(
            status=overall_status,
            database=database_status,
            workflows=workflow_status,
            checks=checks,
        )
        self._record_metrics(kind="readiness", payload=payload)
        return payload

    def _record_metrics(self, *, kind: str, payload: HealthReadinessView) -> None:
        self._observability.observe_health(
            kind=kind,
            overall_status=payload.status,
            checks={name: (check.status, check.required) for name, check in payload.checks.items()},
        )
