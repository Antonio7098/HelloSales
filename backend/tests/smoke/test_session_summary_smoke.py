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
        del messages, tools, context, tool_choice, on_text_delta
        return ToolCallCompletionResult(
            provider=self.provider_name,
            model="fake-model",
            content="tool processed",
            tool_calls=[],
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


async def _wait_for_summary_completion(
    client: AsyncClient,
    session_id: str,
    *,
    attempts: int = 80,
) -> dict[str, Any]:
    for _ in range(attempts):
        response = await client.get(f"/api/sessions/{session_id}")
        payload = _json_dict(response.json()["data"])
        summary = payload.get("summary")
        if (
            isinstance(summary, dict)
            and summary.get("status") in {"completed", "failed"}
            and (
                summary.get("status") == "failed"
                or (
                    payload.get("summary_status") == "completed"
                    and isinstance(payload.get("last_summarized_item_sequence"), int)
                    and int(payload["last_summarized_item_sequence"]) > 0
                )
            )
        ):
            return payload
        await asyncio.sleep(0.02)
    raise AssertionError(f"session {session_id} summary did not complete")


async def test_session_summary_generates_after_configured_turn_cadence(test_settings: Settings) -> None:
    app = create_app(
        test_settings.model_copy(update={"session_summary_turn_interval": 2}),
        overrides=AppOverrides(llm_provider=FakeChatModel()),
    )
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            create_response = await client.post(
                "/api/sessions",
                json={"input_text": "show me the current system status"},
            )
            assert create_response.status_code == 200
            session_id = create_response.json()["data"]["session_id"]

            first_completed = await _wait_for_session_status(
                client,
                session_id,
                target_statuses={"completed"},
            )
            assert first_completed["summary"] is None
            assert first_completed["summary_status"] is None
            assert first_completed["last_summarized_item_sequence"] == 0

            append_response = await client.post(
                f"/api/sessions/{session_id}/messages",
                json={"input_text": "list recent tasks"},
            )
            assert append_response.status_code == 200

            second_completed = await _wait_for_session_status(
                client,
                session_id,
                target_statuses={"completed"},
            )
            assert second_completed["summary_status"] in {"queued", "running", "completed"}

            summary_completed = await _wait_for_summary_completion(client, session_id)
            assert summary_completed["status"] == "completed"
            assert summary_completed["summary_status"] == "completed"
            assert summary_completed["summary_task_id"] is not None
            assert summary_completed["last_summarized_item_sequence"] > 0

            summary = _json_dict(summary_completed["summary"])
            assert summary["status"] == "completed"
            assert summary["task_id"] == summary_completed["summary_task_id"]
            assert summary["coverage_start_sequence"] == 1
            assert summary["coverage_end_sequence"] == summary_completed["last_summarized_item_sequence"]
            assert summary["prompt_id"] == "session.summary.compaction"
            assert summary["prompt_version"] == "v1"
            assert summary["provider_name"] == "fake-agent"
            assert summary["model_name"] == "fake-model"
            assert summary["summary_text"].startswith("processed:")

            items_response = await client.get(f"/api/sessions/{session_id}/items")
            assert items_response.status_code == 200
            items = items_response.json()["data"]
            assert len([item for item in items if item["item_type"] == "assistant_message"]) == 2
            assert len([item for item in items if item["item_type"] == "user_message"]) == 2
