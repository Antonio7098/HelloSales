from __future__ import annotations

import asyncio

import httpx

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


async def test_worker_runs_endpoint_smoke(test_settings: Settings) -> None:
    # The smoke fixture builds the default app without overrides, so this test uses a local app.
    from hello_sales_backend.app import create_app

    local_app = create_app(
        test_settings,
        overrides=AppOverrides(
            auth_provider=build_test_auth_provider(),
            llm_provider=FakeWorkerProvider(),
        ),
    )
    async with local_app.router.lifespan_context(local_app):
        transport = httpx.ASGITransport(app=local_app, raise_app_exceptions=True)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as local_client:
            attach_test_session_cookie(local_client)
            start = await local_client.post(
                "/api/worker-runs",
                json={"worker_name": "structured-brief", "input_payload": {"text": "smoke worker"}},
            )
            assert start.status_code == 200
            run_id = start.json()["data"]["run_id"]
            for _ in range(50):
                detail = await local_client.get(f"/api/worker-runs/{run_id}")
                payload = detail.json()["data"]
                if payload["status"] == "completed":
                    break
                await asyncio.sleep(0.02)
            else:
                raise AssertionError("worker smoke run did not complete")

            events = await local_client.get(f"/api/worker-runs/{run_id}/events")

    assert payload["provider_name"] == "fake-worker"
    assert any(item["event_type"] == "worker.run.completed" for item in events.json()["data"])
