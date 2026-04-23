"""Stageflow runtime wrapper."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.workflows.pipeline import (
    WorkflowPipeline,
    WorkflowPipelineFactory,
    WorkflowStageKind,
    WorkflowStageOutput,
    WorkflowStageSpec,
)
from hello_sales_backend.shared.errors import orchestration_error


def _uuid_or_none(value: str | None) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(value)
    except ValueError:
        try:
            return UUID(hex=value)
        except ValueError:
            return None


class StageScopedIdempotencyInterceptor:
    """Stageflow idempotency interceptor scoped to individual stages."""

    name = "idempotency"
    priority = 4

    def __init__(self, *, idempotency_module: Any, store: Any) -> None:
        self._delegate = idempotency_module.IdempotencyInterceptor(
            store=store,
            key_extractor=self._extract_key,
        )

    @staticmethod
    def _extract_key(ctx: Any) -> str | None:
        key = ctx.data.get("idempotency_key")
        stage_name = ctx.data.get("_idempotency_stage_name")
        if not key or not stage_name:
            return None
        return f"{key}:{stage_name}"

    async def before(self, stage_name: str, ctx: Any) -> Any:
        ctx.data["_idempotency_stage_name"] = stage_name
        return await self._delegate.before(stage_name, ctx)

    async def after(self, stage_name: str, result: Any, ctx: Any) -> None:
        ctx.data["_idempotency_stage_name"] = stage_name
        await self._delegate.after(stage_name, result, ctx)
        ctx.data.pop("_idempotency_stage_name", None)

    async def on_error(self, stage_name: str, error: Exception, ctx: Any) -> Any:
        ctx.data["_idempotency_stage_name"] = stage_name
        action = await self._delegate.on_error(stage_name, error, ctx)
        ctx.data.pop("_idempotency_stage_name", None)
        return action


@dataclass(slots=True)
class StageflowPipelineAdapter:
    """Adapt a Stageflow pipeline to the platform pipeline contract."""

    pipeline: Any

    async def run(self) -> dict[str, WorkflowStageOutput]:
        results = await self.pipeline.run()
        return normalize_stageflow_results(results)


def normalize_stageflow_results(results: dict[str, Any]) -> dict[str, WorkflowStageOutput]:
    """Normalize Stageflow stage results to the platform contract."""

    return {
        name: WorkflowStageOutput(data=dict(stage_output.data))
        for name, stage_output in results.items()
    }


@dataclass(slots=True)
class StageflowExecutionSupport:
    """App-owned Stageflow execution helpers."""

    api: Any
    advanced: Any
    subpipeline: Any
    idempotency_store: Any = field(init=False)
    child_spawner: Any = field(init=False)
    idempotency_module: Any = field(init=False)

    def __post_init__(self) -> None:
        self.idempotency_module = importlib.import_module("stageflow.pipeline.idempotency")
        self.idempotency_store = self.idempotency_module.InMemoryIdempotencyStore()
        self.child_spawner = self.subpipeline.get_subpipeline_spawner()

    def build_interceptors(self) -> list[Any]:
        """Build the default interceptor stack with shared idempotency state."""
        interceptors = self.advanced.get_default_interceptors(
            include_auth=False,
            include_idempotency=False,
        )
        interceptors.insert(
            1,
            StageScopedIdempotencyInterceptor(
                idempotency_module=self.idempotency_module,
                store=self.idempotency_store,
            ),
        )
        return sorted(interceptors, key=lambda interceptor: interceptor.priority)

    def build_context(
        self,
        *,
        request_id: str | None,
        trace_id: str | None,
        workflow_name: str,
        execution_mode: str,
        service: str,
        actor_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        """Build a PipelineContext carrying app correlation and workflow data."""

        metadata: dict[str, Any] = {}
        if trace_id is not None:
            metadata["trace_id"] = trace_id
        return self.api.PipelineContext(
            pipeline_run_id=uuid4(),
            request_id=_uuid_or_none(request_id) or uuid4(),
            session_id=uuid4(),
            user_id=_uuid_or_none(actor_id),
            topology=workflow_name,
            execution_mode=execution_mode,
            metadata=metadata,
            service=service,
            data=data or {},
        )

    async def run_pipeline(
        self,
        pipeline: StageflowPipelineAdapter,
        *,
        ctx: Any,
        guard_retry_strategy: Any = None,
    ) -> dict[str, WorkflowStageOutput]:
        """Run one pipeline with the shared interceptor stack."""

        results = await pipeline.pipeline.run(
            ctx,
            interceptors=self.build_interceptors(),
            guard_retry_strategy=guard_retry_strategy,
        )
        return normalize_stageflow_results(results)

    async def run_subpipeline(
        self,
        *,
        parent_ctx: Any,
        parent_stage_name: str,
        correlation_id: UUID,
        pipeline: StageflowPipelineAdapter,
        result_stage_name: str,
        execution_mode: str,
        data_overrides: dict[str, Any] | None = None,
        guard_retry_strategy: Any = None,
    ) -> Any:
        """Run a child pipeline with Stageflow child-run lineage preserved."""

        async def _runner(child_ctx: Any) -> dict[str, Any]:
            results = await pipeline.pipeline.run(
                child_ctx,
                interceptors=self.build_interceptors(),
                guard_retry_strategy=guard_retry_strategy,
            )
            normalized = normalize_stageflow_results(results)
            stage_summaries = {
                stage_name: {
                    "status": output.status.value,
                    "duration_ms": output.duration_ms,
                }
                for stage_name, output in results.items()
            }
            return {
                "payload": normalized[result_stage_name].data,
                "stage_results": stage_summaries,
            }

        return await self.child_spawner.spawn(
            pipeline_name=pipeline.pipeline.name,
            ctx=parent_ctx,
            correlation_id=correlation_id,
            parent_stage_id=parent_stage_name,
            runner=_runner,
            topology=pipeline.pipeline.name,
            execution_mode=execution_mode,
            inherit_data=True,
            data_overrides=data_overrides or {},
        )


@dataclass(slots=True)
class StageflowPipelineFactory:
    """Wrap Stageflow pipeline construction behind a platform-owned interface."""

    api: Any

    def create_pipeline(self, *, name: str, stages: list[WorkflowStageSpec]) -> WorkflowPipeline:
        pipeline = self.api.Pipeline.from_stages(
            *[
                self.api.stage(
                    stage.name,
                    stage.handler,
                    self._map_stage_kind(stage.kind),
                    dependencies=stage.dependencies,
                )
                for stage in stages
            ],
            name=name,
        )
        return StageflowPipelineAdapter(pipeline=pipeline)

    def _map_stage_kind(self, kind: WorkflowStageKind) -> Any:
        if kind is WorkflowStageKind.GUARD:
            return self.api.StageKind.GUARD
        if kind is WorkflowStageKind.WORK:
            return self.api.StageKind.WORK
        return self.api.StageKind.TRANSFORM


@dataclass(slots=True)
class WorkflowRuntime:
    """Resolved orchestration runtime capabilities."""

    installed: bool
    required: bool
    engine_name: str
    pipeline_factory: WorkflowPipelineFactory | None = None
    stageflow_support: StageflowExecutionSupport | None = None


def build_workflow_runtime(settings: Settings) -> WorkflowRuntime:
    """Build the Stageflow runtime wrapper."""

    try:
        importlib.import_module("stageflow")
        stageflow_api_module = importlib.import_module("stageflow.api")
        stageflow_advanced_module = importlib.import_module("stageflow.advanced")
        stageflow_subpipeline_module = importlib.import_module("stageflow.pipeline.subpipeline")
    except ModuleNotFoundError as exc:
        if settings.stageflow_required:
            raise orchestration_error(
                "Stageflow runtime is required but not installed",
                code="workflow.runtime.missing_dependency",
                details={"engine": "stageflow", "required": True},
                exc=exc,
            ) from exc
        return WorkflowRuntime(
            installed=False,
            required=False,
            engine_name="stageflow",
            pipeline_factory=None,
            stageflow_support=None,
        )

    return WorkflowRuntime(
        installed=True,
        required=settings.stageflow_required,
        engine_name="stageflow",
        pipeline_factory=StageflowPipelineFactory(api=stageflow_api_module),
        stageflow_support=StageflowExecutionSupport(
            api=stageflow_api_module,
            advanced=stageflow_advanced_module,
            subpipeline=stageflow_subpipeline_module,
        ),
    )
