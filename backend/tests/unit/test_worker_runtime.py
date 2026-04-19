from __future__ import annotations

from hello_sales_backend.application.workers.bootstrap import build_worker_registry
from hello_sales_backend.platform.llm import (
    JSONGenerationResult,
    LLMCallContext,
    LLMMessage,
    TextGenerationResult,
)
from hello_sales_backend.platform.observability.runtime import (
    AlertPolicy,
    InMemoryOperationalStore,
    ObservabilityRuntime,
)
from hello_sales_backend.platform.workers import (
    InMemoryWorkerStore,
    WorkerExecutionMode,
    WorkerRun,
    WorkerRunStatus,
)
from hello_sales_backend.platform.workers.runtime import WorkerRuntime


class FakeJSONProvider:
    def __init__(self, *, provider_name: str, responses: list[JSONGenerationResult]) -> None:
        self.provider_name = provider_name
        self._responses = responses
        self.calls = 0

    async def generate(self, messages: list[LLMMessage]) -> TextGenerationResult:
        return TextGenerationResult(
            provider=self.provider_name, model="fake-model", output_text=messages[-1].content
        )

    async def generate_text(
        self,
        messages: list[LLMMessage],
        *,
        context: LLMCallContext | None = None,
    ) -> TextGenerationResult:
        return TextGenerationResult(
            provider=self.provider_name, model="fake-model", output_text=messages[-1].content
        )

    async def generate_json(
        self,
        messages: list[LLMMessage],
        *,
        schema_hint=None,
        context: LLMCallContext | None = None,
    ) -> JSONGenerationResult:
        index = min(self.calls, len(self._responses) - 1)
        self.calls += 1
        return self._responses[index]

    def is_configured(self) -> bool:
        return True


async def test_worker_runtime_retries_invalid_json_and_completes() -> None:
    store = InMemoryWorkerStore()
    observability = ObservabilityRuntime(
        store=InMemoryOperationalStore(), alert_policy=AlertPolicy()
    )
    provider = FakeJSONProvider(
        provider_name="primary",
        responses=[
            JSONGenerationResult(
                provider="primary", model="fake-model", raw_text="not-json", output_json=None
            ),
            JSONGenerationResult(
                provider="primary",
                model="fake-model",
                raw_text='{"brief":"ok","key_points":["one"],"priority":"medium"}',
                output_json={"brief": "ok", "key_points": ["one"], "priority": "medium"},
            ),
        ],
    )
    runtime = WorkerRuntime(
        llm_provider=provider,
        store=store,
        workers=build_worker_registry(),
        observability=observability,
    )
    run = WorkerRun(
        run_id="worker-run-1",
        worker_name="structured-brief",
        status=WorkerRunStatus.PENDING,
        input_payload={"text": "Summarize this update."},
        request_id="req-1",
        trace_id="0123456789abcdef0123456789abcdef",
        actor_id=None,
        execution_mode=WorkerExecutionMode.DIRECT,
        max_attempts=3,
        timeout_seconds=5.0,
    )
    await store.create_run(run)

    await runtime.process_run(run_id=run.run_id)

    updated = await store.get_run(run.run_id)
    events = await store.list_events(run.run_id)

    assert updated is not None
    assert updated.status == WorkerRunStatus.COMPLETED
    assert updated.attempt_count == 2
    assert updated.output_payload == {"brief": "ok", "key_points": ["one"], "priority": "medium"}
    assert any(item.event_type == "worker.attempt.validation_failed" for item in events)
    assert any(item.event_type == "worker.run.completed" for item in events)


async def test_worker_runtime_uses_backup_provider_on_final_attempt() -> None:
    store = InMemoryWorkerStore()
    observability = ObservabilityRuntime(
        store=InMemoryOperationalStore(), alert_policy=AlertPolicy()
    )
    primary = FakeJSONProvider(
        provider_name="primary",
        responses=[
            JSONGenerationResult(
                provider="primary", model="fake-model", raw_text="bad", output_json=None
            ),
            JSONGenerationResult(
                provider="primary", model="fake-model", raw_text="still-bad", output_json=None
            ),
        ],
    )
    backup = FakeJSONProvider(
        provider_name="backup",
        responses=[
            JSONGenerationResult(
                provider="backup",
                model="backup-model",
                raw_text='{"brief":"fallback","key_points":["two"],"priority":"high"}',
                output_json={"brief": "fallback", "key_points": ["two"], "priority": "high"},
            )
        ],
    )
    runtime = WorkerRuntime(
        llm_provider=primary,
        backup_provider=backup,
        store=store,
        workers=build_worker_registry(),
        observability=observability,
    )
    run = WorkerRun(
        run_id="worker-run-2",
        worker_name="structured-brief",
        status=WorkerRunStatus.PENDING,
        input_payload={"text": "Urgent issue needs a structured brief."},
        request_id="req-2",
        trace_id="0123456789abcdef0123456789abcdef",
        actor_id=None,
        execution_mode=WorkerExecutionMode.DIRECT,
        max_attempts=3,
        timeout_seconds=5.0,
    )
    await store.create_run(run)

    await runtime.process_run(run_id=run.run_id)

    updated = await store.get_run(run.run_id)
    events = await store.list_events(run.run_id)

    assert updated is not None
    assert updated.status == WorkerRunStatus.COMPLETED
    assert updated.attempt_count == 3
    assert updated.provider_name == "backup"
    assert updated.model_name == "backup-model"
    assert any(item.event_type == "worker.fallback.selected" for item in events)
