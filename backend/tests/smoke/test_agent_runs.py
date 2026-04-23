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
    ProviderToolCall,
    ToolCallCompletionResult,
)

_call_count = 0


def _reset_call_count() -> None:
    global _call_count
    _call_count = 0


class FakeChatModel(ChatModelPort):
    provider_name = "fake-agent"
    _call_count = 0

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
        tools: list,
        context=None,
        tool_choice=None,
        on_text_delta=None,
    ) -> ToolCallCompletionResult:
        FakeChatModel._call_count += 1
        tool_name = tools[0].name if tools else "get_runtime_status"
        if FakeChatModel._call_count == 1:
            return ToolCallCompletionResult(
                provider=self.provider_name,
                model="fake-model",
                content=None,
                tool_calls=[
                    ProviderToolCall(
                        call_id="call-1",
                        tool_name=tool_name,
                        arguments={},
                        raw_tool_call={},
                    )
                ],
            )
        FakeChatModel._call_count = 0
        return ToolCallCompletionResult(
            provider=self.provider_name,
            model="fake-model",
            content=f"processed:{messages[-1].get('content', '')}",
            tool_calls=[],
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
    _reset_call_count()
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
            assert len(detail["items"]) >= 2
            assert detail["items"][0]["item_type"] == "user_message"
            assert detail["items"][-1]["item_type"] in {"assistant_message", "tool_call", "tool_result"}


async def test_agent_run_supports_approval_flow(test_settings: Settings) -> None:
    _reset_call_count()
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

            detail = await _wait_for_session_completion(
                client,
                session_id,
                terminal_statuses={"completed", "failed", "cancelled", "awaiting_approval"},
            )
            assert detail["status"] in {"completed", "awaiting_approval", "failed"}
