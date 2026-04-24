from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

import pytest
from httpx import ASGITransport, AsyncClient

from hello_sales_backend.app import create_app
from hello_sales_backend.platform.composition.overrides import AppOverrides
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.providers.llm.contracts import (
    ChatCompletion,
    ChatMessage,
    ChatModelPort,
    JSONGenerationResult,
    ProviderToolCall,
    ProviderToolDefinition,
    ToolCallCompletionResult,
)
from tests.support.auth import attach_test_session_cookie, build_test_auth_provider


class FakeChatModel(ChatModelPort):
    provider_name = "fake-agent"

    async def generate(self, messages: list[ChatMessage]) -> ChatCompletion:
        return ChatCompletion(
            provider=self.provider_name,
            model="fake-model",
            output_text=f"processed:{messages[-1].content}",
        )

    async def generate_text(
        self,
        messages: list[ChatMessage],
        *,
        context=None,
    ) -> ChatCompletion:
        return ChatCompletion(
            provider=self.provider_name,
            model="fake-model",
            output_text=f"processed:{messages[-1].content}",
        )

    async def generate_json(
        self,
        messages: list[ChatMessage],
        *,
        schema_hint=None,
        context=None,
    ) -> JSONGenerationResult:
        return JSONGenerationResult(
            provider=self.provider_name,
            model="fake-model",
            raw_text="{}",
            output_json={},
        )

    async def complete_with_tools(
        self,
        messages: list[dict[str, object]],
        *,
        tools: list[ProviderToolDefinition],
        context=None,
        tool_choice: str | None = None,
        on_text_delta=None,
    ) -> ToolCallCompletionResult:
        del context, tool_choice, on_text_delta
        latest_user = next(
            str(item.get("content"))
            for item in reversed(messages)
            if item.get("role") == "user"
        )
        if any(item.get("role") == "tool" for item in messages):
            return ToolCallCompletionResult(
                provider=self.provider_name,
                model="fake-model",
                content=f"processed:{latest_user}",
            )
        if latest_user.lower().startswith("show"):
            return ToolCallCompletionResult(
                provider=self.provider_name,
                model="fake-model",
                content=f"processed:{latest_user}",
            )
        tool_names = [t.name for t in tools]
        tool_name = tool_names[0] if tool_names else "query_analytics_data"
        arguments = {
            "catalog_id": "scaffold_stage",
            "sql": "SELECT 1",
            "reason": "test",
            "max_rows": 5,
        }
        return ToolCallCompletionResult(
            provider=self.provider_name,
            model="fake-model",
            tool_calls=[
                ProviderToolCall(
                    call_id=f"call-{tool_name}",
                    tool_name=tool_name,
                    arguments=arguments,
                )
            ],
        )

    def is_configured(self) -> bool:
        return True


def _json_dict(payload: object) -> dict[str, Any]:
    return cast(dict[str, Any], payload)


async def _wait_for_session_status(
    client: AsyncClient,
    session_id: str,
    *,
    target_statuses: set[str],
    attempts: int = 50,
) -> dict[str, Any]:
    for _ in range(attempts):
        response = await client.get(f"/api/sessions/{session_id}")
        payload = _json_dict(response.json()["data"])
        if payload["status"] in target_statuses:
            return payload
        await asyncio.sleep(0.02)
    raise AssertionError(f"session {session_id} did not reach one of {sorted(target_statuses)}")


@pytest.mark.asyncio
async def test_agent_runs_are_visible_in_metrics_and_diagnostics(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            environment="test",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'agent-metrics.db'}",
            observability_metrics_enabled=True,
            observability_metrics_endpoint_enabled=True,
        ),
        overrides=AppOverrides(
            auth_provider=build_test_auth_provider(),
            llm_provider=FakeChatModel(),
        ),
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            attach_test_session_cookie(client)
            completed_start = await client.post(
                "/api/sessions",
                json={"input_text": "show me the current system status"},
            )
            assert completed_start.status_code == 200
            completed_session_id = completed_start.json()["data"]["session_id"]
            completed_detail = await _wait_for_session_status(
                client,
                completed_session_id,
                target_statuses={"completed", "awaiting_approval"},
            )

            approval_start = await client.post(
                "/api/sessions",
                json={"input_text": "query the current analytics data"},
            )
            assert approval_start.status_code == 200
            approval_session_id = approval_start.json()["data"]["session_id"]
            awaiting_detail = await _wait_for_session_status(
                client,
                approval_session_id,
                target_statuses={"completed", "awaiting_approval"},
            )

            diagnostics = await client.get("/api/system/diagnostics")
            metrics = await client.get("/metrics")

    assert completed_detail["status"] in {"completed", "awaiting_approval"}
    assert awaiting_detail["status"] in {"completed", "awaiting_approval"}
    diagnostics_payload = diagnostics.json()["data"]
    assert diagnostics_payload["sessions"]["total_count"] == 2
    assert diagnostics_payload["observability"]["metrics"]["agents_enabled"] is True
    assert 'hello_sales_agent_turn_executions_started_total{profile="generic"} 2.0' in metrics.text
    assert (
        'hello_sales_agent_tool_approval_requests_total{profile="generic",tool="query_analytics_data"} 1.0'
        in metrics.text
    )
