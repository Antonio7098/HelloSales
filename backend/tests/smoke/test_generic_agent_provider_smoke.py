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
    turns = result.payload["turns"]
    assert isinstance(turns, list)
    assert len(turns) == 2
    assert turns[-1]["status"] == "completed"
    assert turns[-1]["response_text"] == "processed:list recent tasks"
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
async def test_worker_provider_baseline_smoke_executes_end_to_end(test_settings: Settings) -> None:
    settings = Settings(
        environment="test",
        database_url=test_settings.database_url,
        cors_allowed_origins=test_settings.cors_allowed_origins,
    )
    runner = SmokeRunner(
        build_registry(),
        SmokeContext.create(settings=settings),
    )

    result = await runner.run("worker-provider-baseline")

    assert result.smoke_name == "worker-provider-baseline"
    assert result.payload["status"] == "completed"
    assert result.payload["provider"] == settings.resolved_generic_agent_provider
    assert result.payload["model"] == settings.resolved_generic_agent_model
    assert result.payload["worker_name"] == "structured-brief"
    assert result.payload["attempt_count"] >= 1
    assert result.payload["diagnostics_total_workers"] == 1
    output_payload = result.payload["output_payload"]
    assert isinstance(output_payload, dict)
    assert isinstance(output_payload.get("brief"), str)
    assert isinstance(output_payload.get("key_points"), list)
    assert output_payload.get("priority") in {"low", "medium", "high"}
    event_types = result.payload["event_types"]
    assert isinstance(event_types, list)
    assert "worker.run.completed" in event_types
