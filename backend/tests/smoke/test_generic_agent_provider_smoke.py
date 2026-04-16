from __future__ import annotations

import pytest

from hello_sales_backend.platform.composition.overrides import AppOverrides
from hello_sales_backend.platform.providers.llm.contracts import ChatCompletion, ChatMessage, ChatModelPort
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

    def is_configured(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_generic_agent_provider_smoke_executes_end_to_end(test_settings):
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
