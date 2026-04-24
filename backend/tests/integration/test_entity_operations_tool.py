from __future__ import annotations

import asyncio
import json
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


class FakeEntityMutationChatModel(ChatModelPort):
    provider_name = "fake-entity-mutations"

    async def generate(self, messages: list[ChatMessage]) -> ChatCompletion:
        return await self.generate_text(messages)

    async def generate_text(
        self,
        messages: list[ChatMessage],
        *,
        context=None,
    ) -> ChatCompletion:
        del context
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
        del messages, schema_hint, context
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
        latest_user = next(str(item.get("content")) for item in reversed(messages) if item.get("role") == "user")
        tool_messages = [
            json.loads(str(item.get("content")))
            for item in messages
            if item.get("role") == "tool"
        ]
        if not tool_messages:
            return ToolCallCompletionResult(
                provider=self.provider_name,
                model="fake-model",
                tool_calls=[
                    ProviderToolCall(
                        call_id="call-create-entity",
                        tool_name=next(tool.name for tool in tools if tool.name == "create_entity"),
                        arguments={
                            "entity_type": "company_profile",
                            "values": {
                                "company_name": "HelloSales",
                                "industry": "B2B SaaS",
                            },
                            "reason": "Create the company profile",
                        },
                    )
                ],
            )
        if len(tool_messages) == 1:
            created = tool_messages[0]
            return ToolCallCompletionResult(
                provider=self.provider_name,
                model="fake-model",
                tool_calls=[
                    ProviderToolCall(
                        call_id="call-edit-entity",
                        tool_name=next(tool.name for tool in tools if tool.name == "edit_entity"),
                        arguments={
                            "entity_ref": created["entity_ref"],
                            "changes": {"quarterly_sales_focus": "Improve close rate"},
                            "expected_version": created["version"],
                            "reason": "Update the current focus",
                        },
                    )
                ],
            )
        return ToolCallCompletionResult(
            provider=self.provider_name,
            model="fake-model",
            content=f"processed:{latest_user}",
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
    attempts: int = 200,
) -> dict[str, Any]:
    for _ in range(attempts):
        response = await client.get(f"/api/sessions/{session_id}")
        payload = _json_dict(response.json()["data"])
        if payload["status"] in target_statuses:
            return payload
        await asyncio.sleep(0.02)
    raise AssertionError(f"session {session_id} did not reach one of {sorted(target_statuses)}")


async def _wait_for_session_snapshot(
    client: AsyncClient,
    session_id: str,
    *,
    predicate,
    attempts: int = 200,
) -> dict[str, Any]:
    for _ in range(attempts):
        response = await client.get(f"/api/sessions/{session_id}")
        payload = _json_dict(response.json()["data"])
        if predicate(payload):
            return payload
        await asyncio.sleep(0.02)
    raise AssertionError(f"session {session_id} did not reach the expected snapshot")


@pytest.mark.asyncio
async def test_entity_mutation_tools_create_then_edit_with_approval_boundaries(
    test_settings: Settings,
) -> None:
    app = create_app(
        test_settings,
        overrides=AppOverrides(
            auth_provider=build_test_auth_provider(),
            llm_provider=FakeEntityMutationChatModel(),
        ),
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            attach_test_session_cookie(client)
            start = await client.post(
                "/api/sessions",
                json={"input_text": "Create the company profile and then update the quarterly focus"},
            )
            assert start.status_code == 200
            session_id = start.json()["data"]["session_id"]

            first_pending = await _wait_for_session_status(
                client,
                session_id,
                target_statuses={"awaiting_approval"},
            )
            first_tool_call = next(item for item in first_pending["items"] if item["item_type"] == "tool_call")
            assert first_tool_call["payload"]["tool_name"] == "create_entity"
            first_approval_id = first_tool_call["payload"]["approval_id"]
            assert isinstance(first_approval_id, str)

            approved_first = await client.post(
                f"/api/sessions/approvals/{first_approval_id}",
                json={"approved": True},
            )
            assert approved_first.status_code == 200

            second_pending = await _wait_for_session_snapshot(
                client,
                session_id,
                predicate=lambda payload: payload["status"] == "awaiting_approval"
                and any(
                    item["item_type"] == "tool_call"
                    and item["payload"]["tool_name"] == "edit_entity"
                    for item in payload["items"]
                ),
            )
            tool_calls = [item for item in second_pending["items"] if item["item_type"] == "tool_call"]
            second_tool_call = tool_calls[-1]
            assert second_tool_call["payload"]["tool_name"] == "edit_entity"
            second_approval_id = second_tool_call["payload"]["approval_id"]
            assert isinstance(second_approval_id, str)

            approved_second = await client.post(
                f"/api/sessions/approvals/{second_approval_id}",
                json={"approved": True},
            )
            assert approved_second.status_code == 200

            completed = await _wait_for_session_status(
                client,
                session_id,
                target_statuses={"completed"},
            )
            assert completed["status"] == "completed"
            assert completed["items"][-1]["item_type"] == "assistant_message"

            tool_results = [item for item in completed["items"] if item["item_type"] == "tool_result"]
            create_result = next(item for item in tool_results if item["payload"]["tool_name"] == "create_entity")
            edit_result = next(item for item in tool_results if item["payload"]["tool_name"] == "edit_entity")

            assert create_result["payload"]["result"]["catalog_id"] == "scaffold_stage"
            assert create_result["payload"]["result"]["catalog_version"] == "2026-04-23"
            assert create_result["payload"]["result"]["undo_status"] == "unavailable"
            assert create_result["payload"]["result"]["entity_ref"].startswith("ctx_entity_")
            assert edit_result["payload"]["result"]["catalog_id"] == "scaffold_stage"
            assert edit_result["payload"]["result"]["catalog_version"] == "2026-04-23"
            assert edit_result["payload"]["result"]["undo_status"] == "available"
            assert edit_result["payload"]["result"]["changed_fields"] == ["quarterly_sales_focus"]
            assert edit_result["payload"]["result"]["entity_ref"].startswith("ctx_entity_")

            profile_response = await client.get("/api/company-profile")
            assert profile_response.status_code == 200
            profile = profile_response.json()["data"]
            assert profile["company_name"] == "HelloSales"
            assert profile["quarterly_sales_focus"] == "Improve close rate"

            events = app.state.container.observability.recent_events(limit=20)
            event_types = [event.event_type for event in events]
            assert "entity_operations.mutation.created" in event_types
            assert "entity_operations.mutation.updated" in event_types
