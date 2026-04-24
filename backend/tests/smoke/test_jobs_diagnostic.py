from __future__ import annotations

import asyncio

from httpx import ASGITransport, AsyncClient

from hello_sales_backend.app import create_app
from hello_sales_backend.platform.composition.overrides import AppOverrides
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.providers.llm.contracts import (
    ChatCompletion,
    ChatMessage,
    ChatModelPort,
    JSONGenerationResult,
)
from tests.support.auth import attach_test_session_cookie, build_test_auth_provider


class FakeChatModel(ChatModelPort):
    provider_name = "fake-diagnostic"

    async def generate(self, messages: list[ChatMessage]) -> ChatCompletion:
        return ChatCompletion(provider=self.provider_name, model="fake-model", output_text="OK")

    async def generate_text(
        self,
        messages: list[ChatMessage],
        *,
        context=None,
    ) -> ChatCompletion:
        return ChatCompletion(provider=self.provider_name, model="fake-model", output_text="OK")

    async def generate_json(
        self,
        messages: list[ChatMessage],
        *,
        schema_hint=None,
        context=None,
    ) -> JSONGenerationResult:
        return JSONGenerationResult(
            provider=self.provider_name, model="fake-model", raw_text="{}", output_json={}
        )

    def is_configured(self) -> bool:
        return True


async def test_jobs_diagnostic_workflow_runs(client: AsyncClient, test_settings: Settings) -> None:
    app = create_app(
        test_settings,
        overrides=AppOverrides(
            auth_provider=build_test_auth_provider(),
            llm_provider=FakeChatModel(),
        ),
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as local_client:
            attach_test_session_cookie(local_client)
            response = await local_client.post("/api/jobs/diagnostic", json={"prompt": "Say OK"})
            assert response.status_code == 200
            task_id = response.json()["data"]["task_id"]

            await asyncio.sleep(0.05)

            list_response = await local_client.get("/api/jobs/tasks")
            assert list_response.status_code == 200
            items = list_response.json()["data"]["items"]
            assert any(item["task_id"] == task_id for item in items)

            detail_response = await local_client.get(f"/api/jobs/tasks/{task_id}")
            assert detail_response.status_code == 200
            detail = detail_response.json()["data"]
            assert detail["task_id"] == task_id
            assert detail["status"] in {"completed", "running"}
