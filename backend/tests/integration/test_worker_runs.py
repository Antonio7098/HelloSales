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


async def _poll_worker_completion(client: AsyncClient, run_id: str) -> dict[str, object]:
    for _ in range(50):
        response = await client.get(f"/api/worker-runs/{run_id}")
        payload = response.json()["data"]
        if payload["status"] in {"completed", "failed", "cancelled"}:
            return dict(payload)  # type: ignore[arg-type]
        await asyncio.sleep(0.02)
    raise AssertionError("worker run did not complete in time")


@pytest.mark.asyncio
async def test_worker_run_is_visible_in_metrics_and_diagnostics(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            environment="test",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'worker-metrics.db'}",
            observability_metrics_enabled=True,
            observability_metrics_endpoint_enabled=True,
        ),
        overrides=AppOverrides(llm_provider=FakeWorkerProvider()),
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
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
        overrides=AppOverrides(llm_provider=FakeWorkerProvider()),
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
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
