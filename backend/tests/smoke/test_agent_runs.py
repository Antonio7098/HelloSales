from __future__ import annotations

import asyncio
from typing import Any, cast

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

    def is_configured(self) -> bool:
        return True


def _json_dict(payload: object) -> dict[str, Any]:
    return cast(dict[str, Any], payload)


async def _wait_for_session_completion(
    client: AsyncClient,
    session_id: str,
    *,
    attempts: int = 20,
    terminal_statuses: set[str] | None = None,
) -> dict[str, Any]:
    target_statuses = terminal_statuses or {"awaiting_approval", "completed", "failed", "cancelled"}
    for _ in range(attempts):
        response = await client.get(f"/api/sessions/{session_id}")
        payload = _json_dict(response.json()["data"])
        if payload["status"] in target_statuses:
            return payload
        await asyncio.sleep(0.02)
    raise AssertionError(f"session {session_id} did not reach a terminal state")


async def test_agent_run_executes_tools_and_completes(test_settings: Settings) -> None:
    app = create_app(
        test_settings,
        overrides=AppOverrides(llm_provider=FakeChatModel()),
    )
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            start_response = await client.post(
                "/api/sessions",
                json={"input_text": "show me the current system status"},
            )
            assert start_response.status_code == 200
            session_id = start_response.json()["data"]["session_id"]

            detail = await _wait_for_session_completion(client, session_id)

            assert detail["status"] == "completed"
            assert len(detail["items"]) >= 3
            assert detail["items"][0]["item_type"] == "user_message"
            assert detail["items"][1]["item_type"] == "tool_call"
            assert detail["items"][1]["payload"]["tool_name"] == "get_runtime_status"
            assert detail["items"][2]["item_type"] in {"tool_result", "assistant_message"}
            assert any(
                item["item_type"] == "assistant_message"
                and item["payload"]["text"] == "processed:show me the current system status"
                for item in detail["items"]
            )

            events_response = await client.get(f"/api/sessions/{session_id}/events")
            assert events_response.status_code == 200
            event_types = [item["event_type"] for item in events_response.json()["data"]]
            assert "agent.turn.started" in event_types
            assert "agent.tool.completed" in event_types
            assert "agent.turn.completed" in event_types


async def test_agent_run_supports_approval_flow(test_settings: Settings) -> None:
    app = create_app(
        test_settings,
        overrides=AppOverrides(llm_provider=FakeChatModel()),
    )
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            start_response = await client.post(
                "/api/sessions",
                json={"input_text": "please run diagnostic job now"},
            )
            assert start_response.status_code == 200
            session_id = start_response.json()["data"]["session_id"]

            awaiting_detail = await _wait_for_session_completion(client, session_id)
            assert awaiting_detail["status"] == "awaiting_approval"
            tool_call_item = next(item for item in awaiting_detail["items"] if item["item_type"] == "tool_call")
            approval_id = tool_call_item["payload"]["approval_id"]
            assert approval_id is not None

            approval_response = await client.post(
                f"/api/sessions/approvals/{approval_id}",
                json={"approved": True},
            )
            assert approval_response.status_code == 200
            assert approval_response.json()["data"]["status"] == "approved"

            completed_detail = await _wait_for_session_completion(
                client,
                session_id,
                terminal_statuses={"completed", "failed", "cancelled"},
            )
            assert completed_detail["status"] == "completed"
            assert any(
                item["item_type"] == "assistant_message"
                and item["payload"]["text"] == "processed:please run diagnostic job now"
                for item in completed_detail["items"]
            )
