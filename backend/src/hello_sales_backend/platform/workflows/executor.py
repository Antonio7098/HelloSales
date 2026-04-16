"""App-owned workflow execution facade."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from hello_sales_backend.platform.observability.logging import get_logger
from hello_sales_backend.platform.providers.llm.contracts import ChatMessage, ChatModelPort
from hello_sales_backend.platform.tasks.models import TaskMetadata
from hello_sales_backend.platform.workflows.runtime import WorkflowRuntime


@dataclass(slots=True)
class WorkflowExecutor:
    """Thin execution facade used by modules."""

    runtime: WorkflowRuntime
    _logger: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = get_logger("hello_sales_backend.workflows")

    async def is_available(self) -> bool:
        return self.runtime.installed

    async def run_diagnostic_workflow(
        self,
        *,
        metadata: TaskMetadata,
        llm_provider: ChatModelPort,
        messages: list[ChatMessage],
    ) -> dict[str, object]:
        """Execute a minimal Stageflow-backed diagnostic workflow."""

        if not self.runtime.installed:
            raise RuntimeError("Workflow runtime is not installed")
        api = self.runtime.runtime_objects["api"]
        Pipeline = api.Pipeline
        StageKind = api.StageKind
        stage = api.stage

        async def input_guard(_ctx):
            return {"message_count": len(messages)}

        async def provider_check(_ctx):
            completion = await llm_provider.generate(messages)
            return completion.model_dump(mode="json")

        async def summarize(ctx):
            stage_output = ctx.inputs.get_output("provider_check")
            if stage_output is None:
                raise RuntimeError("Diagnostic workflow provider stage output is missing")
            result = stage_output.data
            return {
                "workflow_name": "diagnostic_llm_workflow",
                "provider": result["provider"],
                "model": result["model"],
                "output_text": result["output_text"],
            }

        pipeline = Pipeline.from_stages(
            stage("input_guard", input_guard, StageKind.GUARD),
            stage("provider_check", provider_check, StageKind.WORK, dependencies=("input_guard",)),
            stage("summarize", summarize, StageKind.TRANSFORM, dependencies=("provider_check",)),
            name="diagnostic_llm_workflow",
        )
        started_at = perf_counter()
        self._logger.info(
            "workflow.started",
            workflow_name="diagnostic_llm_workflow",
            task_id=metadata.task_id,
            provider=llm_provider.provider_name,
        )
        try:
            results = await pipeline.run()
            output = results["summarize"].data
            self._logger.info(
                "workflow.completed",
                workflow_name="diagnostic_llm_workflow",
                task_id=metadata.task_id,
                provider=llm_provider.provider_name,
                duration_ms=round((perf_counter() - started_at) * 1000, 2),
            )
            return output
        except Exception:
            self._logger.exception(
                "workflow.failed",
                workflow_name="diagnostic_llm_workflow",
                task_id=metadata.task_id,
                provider=llm_provider.provider_name,
                duration_ms=round((perf_counter() - started_at) * 1000, 2),
            )
            raise
