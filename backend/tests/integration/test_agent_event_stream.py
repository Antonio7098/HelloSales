from __future__ import annotations

import asyncio
import json
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
    ProviderToolDefinition,
    TextDeltaCallback,
    ToolCallCompletionResult,
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
        context: object | None = None,
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
        schema_hint: object | None = None,
        context: object | None = None,
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
        context: object | None = None,
        tool_choice: str | None = None,
        on_text_delta: TextDeltaCallback | None = None,
    ) -> ToolCallCompletionResult:
        del tools, context, tool_choice
        latest_user = next(
            str(item.get("content"))
            for item in reversed(messages)
            if item.get("role") == "user"
        )
        if "stream" in latest_user.lower():
            if on_text_delta is not None:
                await on_text_delta("processed:")
                await on_text_delta(latest_user)
            return ToolCallCompletionResult(
                provider=self.provider_name,
                model="fake-model",
                content=f"processed:{latest_user}",
            )
        if any(item.get("role") == "tool" for item in messages):
            return ToolCallCompletionResult(
                provider=self.provider_name,
                model="fake-model",
                content=f"processed:{latest_user}",
            )
        return ToolCallCompletionResult(
            provider=self.provider_name,
            model="fake-model",
            tool_calls=[
                ProviderToolCall(
                    call_id="call-query-analytics-data",
                    tool_name="query_analytics_data",
                    arguments={
                        "catalog_id": "scaffold_stage",
                        "sql": (
                            "SELECT product_id, product_name, is_primary "
                            "FROM products ORDER BY created_at ASC LIMIT 5"
                        ),
                        "reason": "Read product data",
                        "max_rows": 5,
                    },
                )
            ],
        )

    def is_configured(self) -> bool:
        return True


class LongStreamingFakeChatModel(FakeChatModel):
    async def complete_with_tools(
        self,
        messages: list[dict[str, object]],
        *,
        tools: list[ProviderToolDefinition],
        context: object | None = None,
        tool_choice: str | None = None,
        on_text_delta: TextDeltaCallback | None = None,
    ) -> ToolCallCompletionResult:
        del messages, tools, context, tool_choice
        if on_text_delta is not None:
            for index in range(520):
                await on_text_delta(f"chunk-{index} ")
        return ToolCallCompletionResult(
            provider=self.provider_name,
            model="fake-model",
            content="long streamed response",
        )


def _json_dict(payload: object) -> dict[str, Any]:
    return cast(dict[str, Any], payload)


def _require_int(value: object) -> int:
    if not isinstance(value, int):
        raise AssertionError(f"expected int, got {type(value).__name__}")
    return value


async def _wait_for_session_status(
    client: AsyncClient,
    session_id: str,
    *,
    target_statuses: set[str],
    attempts: int = 30,
) -> dict[str, Any]:
    for _ in range(attempts):
        response = await client.get(f"/api/sessions/{session_id}")
        payload = _json_dict(response.json()["data"])
        if payload["status"] in target_statuses:
            return payload
        await asyncio.sleep(0.02)
    raise AssertionError(f"session {session_id} did not reach one of {sorted(target_statuses)}")


def _parse_sse_events(body: str) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for chunk in body.strip().split("\n\n"):
        if not chunk.strip():
            continue
        entry: dict[str, Any] = {}
        for line in chunk.splitlines():
            if line.startswith("id: "):
                entry["id"] = int(line.removeprefix("id: "))
            elif line.startswith("event: "):
                entry["event"] = line.removeprefix("event: ")
            elif line.startswith("data: "):
                entry["data"] = json.loads(line.removeprefix("data: "))
        parsed.append(entry)
    return parsed


async def test_agent_event_stream_replays_and_tails_run_events(test_settings: Settings) -> None:
    app = create_app(
        test_settings,
        overrides=AppOverrides(llm_provider=FakeChatModel()),
    )
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            start_response = await client.post(
                "/api/sessions",
                json={"input_text": "stream the company profile"},
            )
            session_id = start_response.json()["data"]["session_id"]

            async with client.stream("GET", f"/api/sessions/{session_id}/events/stream") as response:
                assert response.status_code == 200
                assert response.headers["content-type"].startswith("text/event-stream")
                body = "".join([chunk async for chunk in response.aiter_text()])

            events = _parse_sse_events(body)
            event_types = [str(item["event"]) for item in events]

            assert event_types[0] == "agent.turn.started"
            assert "agent.response.delta" in event_types
            assert event_types[-1] == "agent.turn.completed"

            cutoff = _require_int(events[0]["id"])
            async with client.stream(
                "GET", f"/api/sessions/{session_id}/events/stream?after_sequence={cutoff}"
            ) as response:
                replay_body = "".join([chunk async for chunk in response.aiter_text()])

            replay_events = _parse_sse_events(replay_body)
            assert replay_events
            assert min(_require_int(item["id"]) for item in replay_events) > cutoff


async def test_agent_event_stream_pages_beyond_first_event_batch(test_settings: Settings) -> None:
    app = create_app(
        test_settings,
        overrides=AppOverrides(llm_provider=LongStreamingFakeChatModel()),
    )
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            start_response = await client.post(
                "/api/sessions",
                json={"input_text": "stream a long response"},
            )
            session_id = start_response.json()["data"]["session_id"]

            async with client.stream(
                "GET",
                f"/api/sessions/{session_id}/events/stream?after_sequence=10",
            ) as response:
                body = "".join([chunk async for chunk in response.aiter_text()])

            events = _parse_sse_events(body)

            assert len(events) > 500
            assert events[-1]["event"] == "agent.turn.completed"
            assert _require_int(events[-1]["id"]) > 500


async def test_agent_event_log_records_rejection_and_cancellation(test_settings: Settings) -> None:
    app = create_app(
        test_settings,
        overrides=AppOverrides(llm_provider=FakeChatModel()),
    )
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            reject_response = await client.post(
                "/api/sessions",
                json={"input_text": "query the products"},
            )
            reject_session_id = reject_response.json()["data"]["session_id"]
            reject_detail = await _wait_for_session_status(
                client,
                reject_session_id,
                target_statuses={"awaiting_approval"},
            )
            reject_tool_call = next(item for item in reject_detail["items"] if item["item_type"] == "tool_call")
            reject_approval_id = reject_tool_call["payload"]["approval_id"]
            assert reject_approval_id is not None

            approval_response = await client.post(
                f"/api/sessions/approvals/{reject_approval_id}",
                json={"approved": False},
            )
            assert approval_response.status_code == 200

            reject_events = (await client.get(f"/api/sessions/{reject_session_id}/events")).json()[
                "data"
            ]
            reject_types = [item["event_type"] for item in reject_events]
            assert "agent.approval.rejected" in reject_types
            assert "agent.turn.completed" in reject_types

            cancel_response = await client.post(
                "/api/sessions",
                json={"input_text": "query the products"},
            )
            cancel_session_id = cancel_response.json()["data"]["session_id"]
            cancel_detail = await _wait_for_session_status(
                client,
                cancel_session_id,
                target_statuses={"awaiting_approval"},
            )
            cancel_tool_call = next(item for item in cancel_detail["items"] if item["item_type"] == "tool_call")
            assert cancel_tool_call["payload"]["status"] == "pending_approval"

            cancelled = await client.post(f"/api/sessions/{cancel_session_id}/cancel")
            assert cancelled.status_code == 200
            assert cancelled.json()["data"]["status"] == "cancelled"

            cancelled_detail = await _wait_for_session_status(
                client,
                cancel_session_id,
                target_statuses={"cancelled"},
            )
            assert cancelled_detail["status"] == "cancelled"

            cancel_events = (await client.get(f"/api/sessions/{cancel_session_id}/events")).json()[
                "data"
            ]
            cancel_types = [item["event_type"] for item in cancel_events]
            assert "agent.run.cancel_requested" in cancel_types
            assert "agent.tool.cancelled" in cancel_types
            assert "agent.turn.cancelled" in cancel_types
            assert "agent.run.cancelled" in cancel_types
