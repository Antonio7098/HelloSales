from __future__ import annotations

import os

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
    ) -> ToolCallCompletionResult:
        del tools, context, tool_choice
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
        if "diagnostic" in latest_user.lower():
            tool_name = "run_diagnostic_job"
            arguments = {"prompt": latest_user}
        elif "task" in latest_user.lower():
            tool_name = "list_recent_tasks"
            arguments = {"limit": 10}
        else:
            tool_name = "get_runtime_status"
            arguments = {}
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


@pytest.mark.asyncio
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
    assert result.payload["response_text"] == "processed:list recent tasks"
    items = result.payload["items"]
    assert isinstance(items, list)
    assert len([item for item in items if item["item_type"] == "assistant_message"]) == 2
    assistant_messages = [item for item in items if item["item_type"] == "assistant_message"]
    assert assistant_messages[-1]["payload"]["text"] == "processed:list recent tasks"
    scenarios = result.payload["scenarios"]
    assert isinstance(scenarios, list)
    assert {item["name"] for item in scenarios} == {
        "generic_status_completion",
        "observer_status_completion",
        "append_turn_completion",
        "approval_boundary",
        "event_stream_replay",
    }


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
