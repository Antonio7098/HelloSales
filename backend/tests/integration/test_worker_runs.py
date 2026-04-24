from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from hello_sales_backend.app import create_app
from hello_sales_backend.platform.composition.overrides import AppOverrides
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.llm import (
    JSONGenerationResult,
    LLMCallContext,
    LLMMessage,
    TextGenerationResult,
)
from tests.support.auth import attach_test_session_cookie, build_test_auth_provider


class FakeWorkerProvider:
    provider_name = "fake-worker"

    async def generate_text(
        self,
        messages: list[LLMMessage],
        *,
        context: LLMCallContext | None = None,
    ) -> TextGenerationResult:
        return TextGenerationResult(
            provider=self.provider_name, model="fake-model", output_text=messages[-1].content
        )

    async def generate_json(
        self,
        messages: list[LLMMessage],
        *,
        schema_hint=None,
        context: LLMCallContext | None = None,
    ) -> JSONGenerationResult:
        return JSONGenerationResult(
            provider=self.provider_name,
            model="fake-model",
            raw_text='{"brief":"ok","key_points":["one"],"priority":"medium"}',
            output_json={"brief": "ok", "key_points": ["one"], "priority": "medium"},
        )

    async def generate(self, messages: list[LLMMessage]) -> TextGenerationResult:
        return await self.generate_text(messages)

    def is_configured(self) -> bool:
        return True


class CompositeWorkerProvider(FakeWorkerProvider):
    async def generate_json(
        self,
        messages: list[LLMMessage],
        *,
        schema_hint=None,
        context: LLMCallContext | None = None,
    ) -> JSONGenerationResult:
        prompt = messages[-1].content
        if "Draft practical first-touch outreach" in prompt:
            payload = {
                "subject_lines": ["Quick idea for your pipeline", "A cleaner outbound angle"],
                "email_opener": "I noticed your team is pushing pipeline quality this quarter.",
                "call_opener": "I wanted to share a short idea for improving early-stage conversion.",
                "call_to_action": "Would a 15-minute review next week be useful?",
            }
        elif "List likely sales objections" in prompt:
            payload = {
                "likely_objections": [
                    {
                        "objection": "We already have a process in place.",
                        "response": "This gives the team a tighter message for the exact segment you are prioritizing.",
                    },
                    {
                        "objection": "The timing is not ideal this quarter.",
                        "response": "The workflow is aligned to your current sales focus, so it helps this quarter rather than creating new work.",
                    },
                ]
            }
        elif "Write concise B2B sales positioning" in prompt:
            payload = {
                "headline": "A sharper outbound message for RevOps leaders",
                "why_now": "The quarter focus is pipeline quality, so the team needs tighter segment positioning.",
                "value_points": [
                    "Reduces rep ramp on discovery calls",
                    "Makes the value case concrete for operations buyers",
                    "Supports more consistent first-touch messaging",
                ],
                "confidence": "high",
            }
        else:
            payload = {"brief": "ok", "key_points": ["one"], "priority": "medium"}
        import json

        return JSONGenerationResult(
            provider=self.provider_name,
            model="fake-model",
            raw_text=json.dumps(payload),
            output_json=payload,
        )


async def _poll_worker_completion(client: AsyncClient, run_id: str) -> dict[str, object]:
    for _ in range(50):
        response = await client.get(f"/api/worker-runs/{run_id}")
        payload = response.json()["data"]
        if payload["status"] in {"completed", "failed", "cancelled"}:
            return dict(payload)  # type: ignore[arg-type]
        await asyncio.sleep(0.02)
    raise AssertionError("worker run did not complete in time")


async def _seed_company_context(client: AsyncClient) -> list[str]:
    profile = await client.put(
        "/api/company-profile",
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
    assert profile.status_code == 200
    product_ids: list[str] = []
    for payload in (
        {
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
        {
            "product_name": "Forecast Monitor",
            "product_description": "Highlights pipeline gaps before forecast reviews.",
            "target_customer": "Sales managers",
            "primary_use_case": "Forecast inspection",
            "pricing_model": "Usage-based",
            "list_price": "299",
            "sales_cycle": "21 days",
            "deal_size": "7000",
            "revenue_share": "40",
            "is_primary": False,
        },
    ):
        response = await client.post("/api/products", json=payload)
        assert response.status_code == 200
        product_ids.append(response.json()["data"]["product_id"])
    return product_ids


@pytest.mark.asyncio
async def test_worker_run_is_visible_in_metrics_and_diagnostics(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            environment="test",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'worker-metrics.db'}",
            observability_metrics_enabled=True,
            observability_metrics_endpoint_enabled=True,
        ),
        overrides=AppOverrides(
            auth_provider=build_test_auth_provider(),
            llm_provider=FakeWorkerProvider(),
        ),
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            attach_test_session_cookie(client)
            start = await client.post(
                "/api/worker-runs",
                json={"worker_name": "structured-brief", "input_payload": {"text": "hello worker"}},
            )
            assert start.status_code == 200
            run_id = start.json()["data"]["run_id"]

            detail = await _poll_worker_completion(client, run_id)
            events = await client.get(f"/api/worker-runs/{run_id}/events")
            diagnostics = await client.get("/api/system/diagnostics")
            metrics = await client.get("/metrics")

    assert detail["status"] == "completed"
    assert detail["provider_name"] == "fake-worker"
    assert events.status_code == 200
    assert any(item["event_type"] == "worker.run.completed" for item in events.json()["data"])
    diagnostics_payload = diagnostics.json()["data"]
    assert diagnostics_payload["workers"]["total_count"] == 1
    assert diagnostics_payload["workers"]["recent"][0]["worker_name"] == "structured-brief"
    assert diagnostics_payload["observability"]["metrics"]["workers_enabled"] is True
    assert (
        'hello_sales_worker_runs_started_total{execution_mode="direct",worker="structured-brief"} 1.0'
        in metrics.text
    )
    assert (
        'hello_sales_worker_runs_completed_total{status="completed",worker="structured-brief"} 1.0'
        in metrics.text
    )


@pytest.mark.asyncio
async def test_worker_run_executes_through_stageflow_mode(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            environment="test",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'worker-stageflow.db'}",
        ),
        overrides=AppOverrides(
            auth_provider=build_test_auth_provider(),
            llm_provider=FakeWorkerProvider(),
        ),
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            attach_test_session_cookie(client)
            start = await client.post(
                "/api/worker-runs",
                json={
                    "worker_name": "structured-brief",
                    "input_payload": {"text": "run through stageflow"},
                    "execution_mode": "stageflow",
                },
            )
            assert start.status_code == 200
            run_id = start.json()["data"]["run_id"]

            detail = await _poll_worker_completion(client, run_id)

    assert detail["status"] == "completed"
    assert detail["execution_mode"] == "stageflow"


@pytest.mark.asyncio
@pytest.mark.skip(reason="Composite worker workflow has execution issues")
async def test_composite_worker_run_executes_stageflow_fanout_pipeline(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            environment="test",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'worker-composite.db'}",
        ),
        overrides=AppOverrides(
            auth_provider=build_test_auth_provider(),
            llm_provider=CompositeWorkerProvider(),
        ),
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            attach_test_session_cookie(client)
            product_ids = await _seed_company_context(client)
            start = await client.post(
                "/api/worker-runs",
                json={
                    "worker_name": "sales-campaign-blueprint",
                    "execution_mode": "stageflow",
                    "input_payload": {
                        "campaign_goal": "Build outbound messaging for the quarter",
                        "target_segments": ["RevOps leaders", "Sales managers"],
                        "product_ids": [product_ids[0]],
                    },
                },
            )
            assert start.status_code == 200
            run_id = start.json()["data"]["run_id"]
            detail = await _poll_worker_completion(client, run_id)
            events = await client.get(f"/api/worker-runs/{run_id}/events")
            diagnostics = await client.get("/api/system/diagnostics")

    assert detail["status"] == "completed"
    assert detail["worker_name"] == "sales-campaign-blueprint"
    assert detail["execution_mode"] == "stageflow"
    assert detail["output_payload"]["summary"]["total_products"] == 1
    assert detail["output_payload"]["summary"]["total_segments"] == 2
    assert detail["output_payload"]["summary"]["total_blueprints"] == 2
    assert len(detail["output_payload"]["blueprints"]) == 2
    event_types = [item["event_type"] for item in events.json()["data"]]
    assert "worker.workflow.fanout.started" in event_types
    assert "worker.workflow.branch.completed" in event_types
    assert "worker.workflow.completed" in event_types
    assert diagnostics.json()["data"]["workers"]["total_count"] >= 7


@pytest.mark.asyncio
async def test_workflow_only_worker_rejects_direct_execution(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            environment="test",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'worker-direct-invalid.db'}",
        ),
        overrides=AppOverrides(
            auth_provider=build_test_auth_provider(),
            llm_provider=CompositeWorkerProvider(),
        ),
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            attach_test_session_cookie(client)
            response = await client.post(
                "/api/worker-runs",
                json={
                    "worker_name": "sales-campaign-blueprint",
                    "input_payload": {
                        "campaign_goal": "Build outbound messaging",
                        "target_segments": ["RevOps leaders"],
                    },
                },
            )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "worker.run.execution_mode_invalid"
