"""Real-provider smoke suite for the worker runtime."""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel

from hello_sales_backend.shared.errors import app_error

from ..contracts import SmokeCase, SmokeContext
from ..support import app_client, wait_for_terminal_run_state


class WorkerProviderSmokeResult(BaseModel):
    """Serializable result payload for provider-backed worker smoke execution."""

    run_id: str
    status: str
    provider: str
    model: str
    worker_name: str
    attempt_count: int
    output_payload: dict[str, object] | None = None
    event_types: list[str] = []
    diagnostics_total_workers: int | None = None


class WorkerProviderBaselineSmoke(SmokeCase):
    """Run one minimal provider-backed worker execution."""

    name = "worker-provider-baseline"
    description = "Runs one real provider-backed structured worker execution through the HTTP API."

    @staticmethod
    def _settings(context: SmokeContext) -> Any:
        return context.settings

    def _validate_provider_configuration(self, context: SmokeContext) -> None:
        settings = self._settings(context)
        if not settings.resolved_generic_agent_provider:
            raise app_error(
                "Shared LLM provider is not configured",
                code="smoke.worker_provider.missing_provider",
                category="config",
                status_code=500,
                details={"required_env": ["HELLO_SALES_GENERIC_AGENT_PROVIDER", "HELLO_SALES_GENERIC_AGENT_MODEL"]},
                operation="smoke.worker_provider.preflight",
                component="smoke",
            )
        if not settings.resolved_generic_agent_model:
            raise app_error(
                "Shared LLM model is not configured",
                code="smoke.worker_provider.missing_model",
                category="config",
                status_code=500,
                details={"required_env": ["HELLO_SALES_GENERIC_AGENT_MODEL"]},
                operation="smoke.worker_provider.preflight",
                component="smoke",
            )
        if not settings.resolved_generic_agent_api_key:
            raise app_error(
                "Shared LLM API key is not configured",
                code="smoke.worker_provider.missing_api_key",
                category="config",
                status_code=500,
                details={"provider": settings.resolved_generic_agent_provider},
                operation="smoke.worker_provider.preflight",
                component="smoke",
            )

    async def run(self, context: SmokeContext) -> BaseModel:
        self._validate_provider_configuration(context)
        settings = self._settings(context)
        app = context.build_app()
        try:
            async with app_client(app) as client:
                start = await client.post(
                    f"{settings.api_prefix}/worker-runs",
                    json={
                        "worker_name": "structured-brief",
                        "input_payload": {
                            "text": "Summarize the current backend worker runtime foundation in a short structured brief.",
                        },
                    },
                )
                start.raise_for_status()
                run_id = str(start.json()["data"]["run_id"])
                detail = await wait_for_terminal_run_state(
                    client,
                    path=f"{settings.api_prefix}/worker-runs/{run_id}",
                    terminal_statuses={"completed", "failed", "cancelled"},
                )
                if detail["status"] != "completed":
                    raise app_error(
                        "Provider-backed worker smoke did not complete successfully",
                        code="smoke.worker_provider.execution_failed",
                        category="runtime",
                        status_code=500,
                        details={"run_id": run_id, "status": detail["status"]},
                        operation="smoke.worker_provider.run",
                        component="smoke",
                    )
                events_response = await client.get(f"{settings.api_prefix}/worker-runs/{run_id}/events")
                events_response.raise_for_status()
                diagnostics_response = await client.get(f"{settings.api_prefix}/system/diagnostics")
                diagnostics_response.raise_for_status()
        except httpx.HTTPError as exc:
            raise app_error(
                "Worker provider smoke failed during startup or request execution",
                code="smoke.worker_provider.transport_failed",
                category="infrastructure",
                status_code=500,
                details={
                    "provider": settings.resolved_generic_agent_provider,
                    "model": settings.resolved_generic_agent_model,
                    "database_url": settings.database_url,
                    "smoke_name": self.name,
                },
                operation="smoke.worker_provider.run",
                component="smoke",
                exc=exc,
            ) from exc

        events_payload = events_response.json()["data"]
        event_types = [
            item["event_type"] for item in events_payload if isinstance(item, dict) and isinstance(item.get("event_type"), str)
        ]
        diagnostics_payload = diagnostics_response.json()["data"]
        workers_payload = diagnostics_payload.get("workers")
        diagnostics_total_workers = None
        if isinstance(workers_payload, dict):
            total_workers = workers_payload.get("total_count")
            diagnostics_total_workers = int(total_workers) if isinstance(total_workers, int) else None
        attempt_count = detail.get("attempt_count")
        output_payload = detail.get("output_payload")
        return WorkerProviderSmokeResult(
            run_id=run_id,
            status=str(detail["status"]),
            provider=settings.resolved_generic_agent_provider,
            model=settings.resolved_generic_agent_model,
            worker_name=str(detail["worker_name"]),
            attempt_count=attempt_count if isinstance(attempt_count, int) else 0,
            output_payload=output_payload if isinstance(output_payload, dict) else None,
            event_types=event_types,
            diagnostics_total_workers=diagnostics_total_workers,
        )
