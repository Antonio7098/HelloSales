from __future__ import annotations

import os
from typing import Any

import pytest

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
from hello_sales_backend.smoke.__main__ import build_registry
from hello_sales_backend.smoke.contracts import SmokeContext
from hello_sales_backend.smoke.runner import SmokeRunner


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
        on_text_delta: Any = None,
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
        tool_names = [t.name for t in tools]
        tool_name = tool_names[0] if tool_names else "query_analytics_data"
        arguments = {"catalog_id": "scaffold_stage", "sql": "SELECT 1", "reason": "test", "max_rows": 5}
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


def _provider_env_available() -> bool:
    return bool(
        os.getenv("HELLO_SALES_GENERIC_AGENT_PROVIDER")
        and os.getenv("HELLO_SALES_GENERIC_AGENT_MODEL")
        and (
            os.getenv("HELLO_SALES_GROQ_API_KEY")
            or os.getenv("HELLO_SALES_OPENAI_API_KEY")
            or os.getenv("HELLO_SALES_OPENROUTER_API_KEY")
        )
    )


def _real_provider_settings_or_skip(test_settings: Settings) -> Settings:
    configured = Settings()
    provider = configured.resolved_web_search_provider or "tavily"
    settings = test_settings.model_copy(
        update={
            "generic_agent_provider": configured.resolved_generic_agent_provider,
            "generic_agent_model": configured.resolved_generic_agent_model,
            "generic_agent_base_url": configured.generic_agent_base_url,
            "groq_api_key": configured.groq_api_key,
            "openai_api_key": configured.openai_api_key,
            "openrouter_api_key": configured.openrouter_api_key,
            "web_search_provider": provider,
            "web_search_api_key": configured.web_search_api_key,
            "tavily_api_key": configured.tavily_api_key,
        }
    )
    if not settings.resolved_generic_agent_provider:
        pytest.skip("real web-search smoke requires HELLO_SALES_GENERIC_AGENT_PROVIDER")
    if not settings.resolved_generic_agent_model:
        pytest.skip("real web-search smoke requires HELLO_SALES_GENERIC_AGENT_MODEL")
    if not settings.resolved_generic_agent_api_key:
        pytest.skip("real web-search smoke requires a generic-agent provider API key")
    if not settings.resolved_web_search_api_key:
        pytest.skip("real web-search smoke requires HELLO_SALES_TAVILY_API_KEY or HELLO_SALES_WEB_SEARCH_API_KEY")
    return settings


@pytest.mark.asyncio
@pytest.mark.skip(reason="smoke test has complex approval flow - needs real provider or rework")
async def test_generic_agent_provider_smoke_executes_end_to_end(test_settings: Settings) -> None:
    settings = test_settings.model_copy(
        update={
            "generic_agent_provider": "groq",
            "generic_agent_model": "openai/gpt-oss-20b",
            "groq_api_key": "test-key",
        }
    )
    runner = SmokeRunner(
        build_registry(),
        SmokeContext.create(
            settings=settings,
            overrides=AppOverrides(llm_provider=FakeChatModel()),
        ),
    )

    result = await runner.run("generic-agent-provider")

    assert result.smoke_name == "generic-agent-provider"
    assert result.payload["status"] == "completed"
    assert result.payload["provider"] == "groq"
    assert result.payload["model"] == "openai/gpt-oss-20b"
    expected_analytics_prompt = (
        "Use the query_analytics_data tool with catalog_id scaffold_stage to show total meetings by source "
        "from analytics. Return the results only after the approval step completes."
    )
    assert result.payload["response_text"] == f"processed:{expected_analytics_prompt}"
    items = result.payload["items"]
    assert isinstance(items, list)
    assert len([item for item in items if item["item_type"] == "assistant_message"]) >= 1
    assistant_messages = [item for item in items if item["item_type"] == "assistant_message"]
    assert assistant_messages[-1]["payload"]["text"] == f"processed:{expected_analytics_prompt}"
    scenarios = result.payload["scenarios"]
    assert isinstance(scenarios, list)
    assert {item["name"] for item in scenarios} == {
        "generic_status_completion",
        "observer_status_completion",
        "append_turn_completion",
        "approval_boundary",
        "event_stream_replay",
        "analytics_query_completion",
    }
    tool_results = [item for item in items if item["item_type"] == "tool_result"]
    assert any(item["payload"]["tool_name"] == "query_analytics_data" for item in tool_results)


@pytest.mark.asyncio
async def test_generic_agent_web_search_smoke_executes_real_tool_lifecycle(test_settings: Settings) -> None:
    settings = _real_provider_settings_or_skip(test_settings)
    runner = SmokeRunner(
        build_registry(),
        SmokeContext.create(settings=settings),
    )

    result = await runner.run("generic-agent-provider-web-search")

    assert result.smoke_name == "generic-agent-provider-web-search"
    assert result.payload["status"] == "completed"
    assert result.payload["provider"] == settings.resolved_generic_agent_provider
    assert result.payload["model"] == settings.resolved_generic_agent_model
    assert isinstance(result.payload["response_text"], str)
    scenarios = result.payload["scenarios"]
    assert isinstance(scenarios, list)
    assert scenarios[0]["name"] == "web_search_completion"
    assert scenarios[0]["status"] == "completed"
    assert scenarios[0]["details"]["tool_name"] == "search_web"
    assert scenarios[0]["details"]["source_count"] >= 1
    assert scenarios[0]["details"]["provider"] == settings.resolved_web_search_provider
    items = result.payload["items"]
    assert isinstance(items, list)
    tool_calls = [item for item in items if item["item_type"] == "tool_call"]
    tool_results = [item for item in items if item["item_type"] == "tool_result"]
    assert any(item["payload"]["tool_name"] == "search_web" for item in tool_calls)
    search_result = next(item for item in tool_results if item["payload"]["tool_name"] == "search_web")
    assert search_result["payload"]["status"] == "completed"
    assert search_result["payload"]["result"]["provider"] == settings.resolved_web_search_provider
    assert len(search_result["payload"]["result"]["sources"]) >= 1
    assert search_result["payload"]["result"]["sources"][0]["url"].startswith(("http://", "https://"))


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _provider_env_available(),
    reason="real provider smoke requires HELLO_SALES_GENERIC_AGENT_* and provider API key env vars",
)
async def test_generic_agent_provider_baseline_smoke_executes_end_to_end(test_settings: Settings) -> None:
    settings = Settings(
        environment="test",
        database_url=test_settings.database_url,
        cors_allowed_origins=test_settings.cors_allowed_origins,
    )
    runner = SmokeRunner(
        build_registry(),
        SmokeContext.create(settings=settings),
    )

    result = await runner.run("generic-agent-provider-baseline")

    assert result.smoke_name == "generic-agent-provider-baseline"
    assert result.payload["status"] == "completed"
    assert result.payload["provider"] == settings.resolved_generic_agent_provider
    assert result.payload["model"] == settings.resolved_generic_agent_model
    assert isinstance(result.payload["session_id"], str)
    response_text = result.payload["response_text"]
    assert response_text is None or isinstance(response_text, str)
    scenarios = result.payload["scenarios"]
    assert isinstance(scenarios, list)
    assert len(scenarios) == 1
    assert scenarios[0]["name"] == "generic_status_completion"
    assert scenarios[0]["status"] == "completed"
    items = result.payload["items"]
    assert isinstance(items, list)
    assert any(item["item_type"] == "tool_call" for item in items)
    assert any(item["item_type"] == "tool_result" for item in items)
    assert any(item["item_type"] == "assistant_message" for item in items)
