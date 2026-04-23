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


class CampaignWorkflowProviderSmokeResult(WorkerProviderSmokeResult):
    """Serializable result payload for the composite campaign workflow smoke."""

    total_blueprints: int | None = None
    child_worker_run_count: int | None = None


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


class WorkerCampaignWorkflowSmoke(SmokeCase):
    """Run the composite Stageflow worker against a real provider."""

    name = "worker-campaign-workflow"
    description = "Runs the Stageflow sales campaign blueprint workflow with persisted company context."

    @staticmethod
    def _settings(context: SmokeContext) -> Any:
        return context.settings

    def _validate_provider_configuration(self, context: SmokeContext) -> None:
        WorkerProviderBaselineSmoke()._validate_provider_configuration(context)

    async def run(self, context: SmokeContext) -> BaseModel:
        self._validate_provider_configuration(context)
        settings = self._settings(context)
        app = context.build_app()
        try:
            async with app_client(app) as client:
                profile = await client.put(
                    f"{settings.api_prefix}/company-profile",
                    json={
                        "company_name": "HelloSales",
                        "industry": "Sales software",
                        "target_customer": "Mid-market revenue teams",
                        "pricing_model": "Subscription",
                        "sales_team_size": 12,
                        "crm_tool": "HubSpot",
                        "average_deal_size": "12000",
                        "average_sales_cycle": "45 days",
                        "primary_sales_constraint": "Low reply rates",
                        "quarterly_sales_focus": "Improve outbound conversion",
                    },
                )
                profile.raise_for_status()
                product = await client.post(
                    f"{settings.api_prefix}/products",
                    json={
                        "product_name": "Pipeline Copilot",
                        "product_description": "Helps reps prioritize and tailor outbound messaging.",
                        "target_customer": "Revenue operations leaders",
                        "primary_use_case": "Outbound planning",
                        "pricing_model": "Subscription",
                        "list_price": "499",
                        "sales_cycle": "30 days",
                        "deal_size": "10000",
                        "revenue_share": "60",
                        "is_primary": True,
                    },
                )
                product.raise_for_status()
                product_id = str(product.json()["data"]["product_id"])
                start = await client.post(
                    f"{settings.api_prefix}/worker-runs",
                    json={
                        "worker_name": "sales-campaign-blueprint",
                        "execution_mode": "stageflow",
                        "input_payload": {
                            "campaign_goal": "Build outbound messaging for the quarter",
                            "target_segments": ["RevOps leaders", "Sales managers"],
                            "product_ids": [product_id],
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
                        "Provider-backed campaign workflow smoke did not complete successfully",
                        code="smoke.worker_campaign_workflow.execution_failed",
                        category="runtime",
                        status_code=500,
                        details={"run_id": run_id, "status": detail["status"]},
                        operation="smoke.worker_campaign_workflow.run",
                        component="smoke",
                    )
                events_response = await client.get(f"{settings.api_prefix}/worker-runs/{run_id}/events")
                events_response.raise_for_status()
                diagnostics_response = await client.get(f"{settings.api_prefix}/system/diagnostics")
                diagnostics_response.raise_for_status()
        except httpx.HTTPError as exc:
            raise app_error(
                "Worker campaign workflow smoke failed during startup or request execution",
                code="smoke.worker_campaign_workflow.transport_failed",
                category="infrastructure",
                status_code=500,
                details={
                    "provider": settings.resolved_generic_agent_provider,
                    "model": settings.resolved_generic_agent_model,
                    "database_url": settings.database_url,
                    "smoke_name": self.name,
                },
                operation="smoke.worker_campaign_workflow.run",
                component="smoke",
                exc=exc,
            ) from exc

        events_payload = events_response.json()["data"]
        event_types = [
            item["event_type"] for item in events_payload if isinstance(item, dict) and isinstance(item.get("event_type"), str)
        ]
        child_worker_run_count = sum(1 for item in event_types if item == "worker.workflow.child_scheduled")
        output_payload = detail.get("output_payload")
        total_blueprints = None
        if isinstance(output_payload, dict):
            summary = output_payload.get("summary")
            if isinstance(summary, dict) and isinstance(summary.get("total_blueprints"), int):
                total_blueprints = int(summary["total_blueprints"])
        diagnostics_payload = diagnostics_response.json()["data"]
        workers_payload = diagnostics_payload.get("workers")
        diagnostics_total_workers = None
        if isinstance(workers_payload, dict):
            total_workers = workers_payload.get("total_count")
            diagnostics_total_workers = int(total_workers) if isinstance(total_workers, int) else None
        attempt_count = detail.get("attempt_count")
        return CampaignWorkflowProviderSmokeResult(
            run_id=run_id,
            status=str(detail["status"]),
            provider=settings.resolved_generic_agent_provider,
            model=settings.resolved_generic_agent_model,
            worker_name=str(detail["worker_name"]),
            attempt_count=attempt_count if isinstance(attempt_count, int) else 0,
            output_payload=output_payload if isinstance(output_payload, dict) else None,
            event_types=event_types,
            diagnostics_total_workers=diagnostics_total_workers,
            total_blueprints=total_blueprints,
            child_worker_run_count=child_worker_run_count,
        )
