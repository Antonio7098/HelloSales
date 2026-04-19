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


def _require_int(value: object) -> int:
    if not isinstance(value, int):
        raise AssertionError(f"expected int, got {type(value).__name__}")
    return value


async def _wait_for_run_status(
    client: AsyncClient,
    run_id: str,
    *,
    target_statuses: set[str],
    attempts: int = 30,
) -> dict[str, Any]:
    for _ in range(attempts):
        response = await client.get(f"/api/agent-runs/{run_id}")
        payload = _json_dict(response.json()["data"])
        if payload["status"] in target_statuses:
            return payload
        await asyncio.sleep(0.02)
    raise AssertionError(f"run {run_id} did not reach one of {sorted(target_statuses)}")


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
                "/api/agent-runs",
                json={"input_text": "show me the current system status"},
            )
            run_id = start_response.json()["data"]["run_id"]

            async with client.stream("GET", f"/api/agent-runs/{run_id}/events/stream") as response:
                assert response.status_code == 200
                assert response.headers["content-type"].startswith("text/event-stream")
                body = "".join([chunk async for chunk in response.aiter_text()])

            events = _parse_sse_events(body)
            event_types = [str(item["event"]) for item in events]

            assert event_types[0] == "agent.turn.started"
            assert "agent.tool.completed" in event_types
            assert event_types[-1] == "agent.turn.completed"

            cutoff = _require_int(events[0]["id"])
            async with client.stream(
                "GET", f"/api/agent-runs/{run_id}/events/stream?after_sequence={cutoff}"
            ) as response:
                replay_body = "".join([chunk async for chunk in response.aiter_text()])

            replay_events = _parse_sse_events(replay_body)
            assert replay_events
            assert min(_require_int(item["id"]) for item in replay_events) > cutoff


async def test_agent_event_log_records_rejection_and_cancellation(test_settings: Settings) -> None:
    app = create_app(
        test_settings,
        overrides=AppOverrides(llm_provider=FakeChatModel()),
    )
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            reject_response = await client.post(
                "/api/agent-runs",
                json={"input_text": "please run diagnostic job now"},
            )
            reject_run_id = reject_response.json()["data"]["run_id"]
            reject_detail = await _wait_for_run_status(
                client,
                reject_run_id,
                target_statuses={"awaiting_approval"},
            )
            reject_approval_id = reject_detail["turns"][0]["tools"][0]["approval_id"]
            assert reject_approval_id is not None

            approval_response = await client.post(
                f"/api/agent-runs/approvals/{reject_approval_id}",
                json={"approved": False},
            )
            assert approval_response.status_code == 200

            reject_events = (await client.get(f"/api/agent-runs/{reject_run_id}/events")).json()[
                "data"
            ]
            reject_types = [item["event_type"] for item in reject_events]
            assert "agent.approval.rejected" in reject_types
            assert "agent.turn.completed" in reject_types

            cancel_response = await client.post(
                "/api/agent-runs",
                json={"input_text": "please run diagnostic job now"},
            )
            cancel_run_id = cancel_response.json()["data"]["run_id"]
            cancel_detail = await _wait_for_run_status(
                client,
                cancel_run_id,
                target_statuses={"awaiting_approval"},
            )
            cancel_turn = cancel_detail["turns"][0]
            assert cancel_turn["tools"][0]["status"] == "pending_approval"

            cancelled = await client.post(f"/api/agent-runs/{cancel_run_id}/cancel")
            assert cancelled.status_code == 200
            assert cancelled.json()["data"]["status"] == "cancelled"

            cancelled_detail = await _wait_for_run_status(
                client,
                cancel_run_id,
                target_statuses={"cancelled"},
            )
            assert cancelled_detail["turns"][0]["status"] == "cancelled"
            assert cancelled_detail["turns"][0]["tools"][0]["status"] == "cancelled"

            cancel_events = (await client.get(f"/api/agent-runs/{cancel_run_id}/events")).json()[
                "data"
            ]
            cancel_types = [item["event_type"] for item in cancel_events]
            assert "agent.run.cancel_requested" in cancel_types
            assert "agent.tool.cancelled" in cancel_types
            assert "agent.turn.cancelled" in cancel_types
            assert "agent.run.cancelled" in cancel_types
