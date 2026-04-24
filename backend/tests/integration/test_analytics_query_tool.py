from __future__ import annotations

import asyncio
from typing import Any, cast

import pytest
from httpx import ASGITransport, AsyncClient

from hello_sales_backend.app import create_app
from hello_sales_backend.modules.analytics_query.use_cases.commands import (
    QueryAnalyticsDataCommand,
)
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
from hello_sales_backend.shared.errors import AppError
from tests.support.auth import attach_test_session_cookie, build_test_auth_provider


class FakeAnalyticsChatModel(ChatModelPort):
    provider_name = "fake-analytics"

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
        del context, tool_choice
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
        tool_name = next(tool.name for tool in tools if tool.name == "query_analytics_data")
        return ToolCallCompletionResult(
            provider=self.provider_name,
            model="fake-model",
            tool_calls=[
                ProviderToolCall(
                    call_id="call-analytics",
                    tool_name=tool_name,
                    arguments={
                        "catalog_id": "scaffold_stage",
                        "sql": (
                            "SELECT lead_source, SUM(meetings_booked) AS total_meetings "
                            "FROM analytics_daily_pipeline "
                            "GROUP BY lead_source ORDER BY total_meetings DESC"
                        ),
                        "reason": "Summarize meetings booked by source",
                        "max_rows": 5,
                    },
                )
            ],
        )

    def is_configured(self) -> bool:
        return True


class RecoveringAnalyticsChatModel(ChatModelPort):
    provider_name = "fake-analytics-recovering"

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
        del context, tool_choice
        latest_user = next(
            str(item.get("content"))
            for item in reversed(messages)
            if item.get("role") == "user"
        )
        tool_messages = [item for item in messages if item.get("role") == "tool"]
        if tool_messages:
            latest_tool_message = str(tool_messages[-1].get("content"))
            if "analytics_query.validation.unsupported_construct" in latest_tool_message:
                return ToolCallCompletionResult(
                    provider=self.provider_name,
                    model="fake-model",
                    tool_calls=[
                        ProviderToolCall(
                            call_id="call-analytics-corrected",
                            tool_name="query_analytics_data",
                            arguments={
                                "catalog_id": "scaffold_stage",
                                "sql": (
                                    "SELECT lead_source, SUM(meetings_booked) AS total_meetings "
                                    "FROM analytics_daily_pipeline "
                                    "GROUP BY lead_source ORDER BY total_meetings DESC"
                                ),
                                "reason": "Summarize meetings booked by source",
                                "max_rows": 5,
                            },
                        )
                    ],
                )
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
                    call_id="call-analytics-invalid",
                    tool_name="query_analytics_data",
                    arguments={
                        "catalog_id": "scaffold_stage",
                        "sql": "SELECT * FROM analytics_daily_pipeline",
                        "reason": "Inspect analytics rows",
                        "max_rows": 5,
                    },
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
async def test_analytics_query_tool_requires_approval_and_returns_bounded_metadata(
    test_settings: Settings,
) -> None:
    app = create_app(
        test_settings,
        overrides=AppOverrides(
            auth_provider=build_test_auth_provider(),
            llm_provider=FakeAnalyticsChatModel(),
        ),
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            attach_test_session_cookie(client)
            start = await client.post(
                "/api/sessions",
                json={"input_text": "show total meetings by source from analytics"},
            )
            assert start.status_code == 200
            session_id = start.json()["data"]["session_id"]

            awaiting = await _wait_for_session_status(
                client,
                session_id,
                target_statuses={"awaiting_approval"},
            )
            tool_call = next(item for item in awaiting["items"] if item["item_type"] == "tool_call")
            assert tool_call["payload"]["tool_name"] == "query_analytics_data"
            approval_id = tool_call["payload"]["approval_id"]
            assert isinstance(approval_id, str)

            assert tool_call["payload"]["arguments"]["catalog_id"] == "scaffold_stage"
            assert tool_call["payload"]["arguments"]["max_rows"] == 5
            assert "analytics_daily_pipeline" in tool_call["payload"]["arguments"]["sql"]


@pytest.mark.asyncio
async def test_analytics_query_service_emits_validation_failures(test_settings: Settings) -> None:
    app = create_app(test_settings)

    async with app.router.lifespan_context(app):
        with pytest.raises(AppError) as exc_info:
            await app.state.container.modules.analytics_query.service.query_data(
                request_id="req-analytics",
                trace_id="trace-analytics",
                actor_id=None,
                command=QueryAnalyticsDataCommand(
                    catalog_id="scaffold_stage",
                    sql="SELECT lead_source FROM missing_relation",
                    reason="Check missing relation",
                    max_rows=5,
                ),
            )

    assert exc_info.value.code == "analytics_query.validation.forbidden_relation"
    assert exc_info.value.details["catalog_id"] == "scaffold_stage"
    assert exc_info.value.details["catalog_version"] == "2026-04-23"
    recent_events = app.state.container.observability.recent_events(limit=10)
    assert any(event.event_type == "analytics_query.failed" for event in recent_events)


@pytest.mark.asyncio
async def test_analytics_query_service_rejects_unbounded_select_star_and_accepts_correction(
    test_settings: Settings,
) -> None:
    app = create_app(test_settings)

    async with app.router.lifespan_context(app):
        with pytest.raises(AppError) as exc_info:
            await app.state.container.modules.analytics_query.service.query_data(
                request_id="req-analytics",
                trace_id="trace-analytics",
                actor_id=None,
                command=QueryAnalyticsDataCommand(
                    catalog_id="scaffold_stage",
                    sql="SELECT * FROM analytics_daily_pipeline",
                    reason="Inspect analytics rows",
                    max_rows=5,
                ),
            )

        service = app.state.container.modules.analytics_query.service
        catalog = service._catalogs.get_catalog("scaffold_stage")
        validated = service._validator.validate(
            catalog=catalog,
            sql=(
                "SELECT lead_source, SUM(meetings_booked) AS total_meetings "
                "FROM analytics_daily_pipeline "
                "GROUP BY lead_source ORDER BY total_meetings DESC"
            ),
            max_rows=5,
        )

    assert exc_info.value.code == "analytics_query.validation.unsupported_construct"
    assert exc_info.value.message == "SQL contains an unapproved construct"
    assert validated.max_rows == 5
    assert validated.relations == ("analytics_daily_pipeline",)
    assert "aggregate_query" in validated.risk_flags
