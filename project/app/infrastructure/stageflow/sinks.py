"""Stageflow event sinks for observability."""

from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.observability import (
    PipelineEventModel,
    PipelineRunModel,
    ProviderCallModel,
)
from app.infrastructure.telemetry import get_logger
from app.infrastructure.telemetry.metrics import (
    record_llm_request,
    record_pipeline_run,
    record_stage_execution,
)

logger = get_logger(__name__)


class EventSink(Protocol):
    """Protocol for event sinks."""

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit an event."""
        ...

    async def flush(self) -> None:
        """Flush any buffered events."""
        ...


class DbPipelineEventSink:
    """Database sink for pipeline events.

    Persists pipeline run data and events to PostgreSQL for
    observability via the Pulse dashboard.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._pipeline_run_id: UUID | None = None
        self._pipeline_run: PipelineRunModel | None = None
        self._events: list[PipelineEventModel] = []

    async def start_pipeline_run(
        self,
        service: str,
        request_id: str | None = None,
        session_id: UUID | None = None,
        user_id: UUID | None = None,
        org_id: UUID | None = None,
        topology: str | None = None,
        **metadata: Any,
    ) -> UUID:
        """Start a new pipeline run.

        Args:
            service: Service name (e.g., 'chat', 'script_generation')
            request_id: HTTP request correlation ID
            session_id: Chat session ID
            user_id: User ID
            org_id: Organization ID
            topology: Pipeline topology name
            **metadata: Additional metadata

        Returns:
            Pipeline run ID
        """
        now = datetime.now(UTC)
        run_id = uuid4()

        self._pipeline_run = PipelineRunModel(
            id=run_id,
            service=service,
            topology=topology,
            request_id=request_id,
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            success=False,  # Will be updated on completion
            stages={},
            run_metadata=metadata,
            started_at=now,
            created_at=now,
        )
        self._pipeline_run_id = run_id

        self.session.add(self._pipeline_run)
        await self.session.flush()

        logger.debug(
            "Pipeline run started",
            extra={
                "pipeline_run_id": str(run_id),
                "service": service,
            },
        )

        return run_id

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit a pipeline event.

        Args:
            event_type: Event type (e.g., 'stage_started', 'llm_response')
            data: Event data
        """
        if not self._pipeline_run_id:
            logger.warning(
                "Event emitted without active pipeline run",
                extra={"event_type": event_type},
            )
            return

        now = datetime.now(UTC)
        event = PipelineEventModel(
            id=uuid4(),
            pipeline_run_id=self._pipeline_run_id,
            event_type=event_type,
            event_data=data,
            request_id=data.get("request_id"),
            session_id=data.get("session_id"),
            user_id=data.get("user_id"),
            org_id=data.get("org_id"),
            occurred_at=now,
            created_at=now,
        )

        self._events.append(event)
        self.session.add(event)

    async def record_stage_result(
        self,
        stage_name: str,
        status: str,
        latency_ms: int,
        error: str | None = None,
        **data: Any,
    ) -> None:
        """Record a stage execution result.

        Args:
            stage_name: Stage name
            status: Execution status (success, failure, skipped)
            latency_ms: Execution latency in milliseconds
            error: Error message if failed
            **data: Additional stage data
        """
        if self._pipeline_run:
            stages = self._pipeline_run.stages or {}
            stages[stage_name] = {
                "status": status,
                "latency_ms": latency_ms,
                "error": error,
                **data,
            }
            self._pipeline_run.stages = stages

        await self.emit(
            f"stage_{status}",
            {
                "stage": stage_name,
                "latency_ms": latency_ms,
                "error": error,
                **data,
            },
        )

    async def record_provider_call(
        self,
        service: str,
        operation: str,
        provider: str,
        model_id: str | None = None,
        latency_ms: int | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        cost_cents: int | None = None,
        success: bool = True,
        error: str | None = None,
        **data: Any,
    ) -> UUID:
        """Record an external provider call.

        Args:
            service: Service classification
            operation: Operation type (llm, stt, tts)
            provider: Provider name
            model_id: Model identifier
            latency_ms: Call latency
            tokens_in: Input tokens
            tokens_out: Output tokens
            cost_cents: Cost in cents
            success: Whether the call succeeded
            error: Error message if failed
            **data: Additional call data

        Returns:
            Provider call ID
        """
        now = datetime.now(UTC)
        call_id = uuid4()

        call = ProviderCallModel(
            id=call_id,
            service=service,
            operation=operation,
            provider=provider,
            model_id=model_id,
            pipeline_run_id=self._pipeline_run_id,
            request_id=data.get("request_id"),
            session_id=data.get("session_id"),
            user_id=data.get("user_id"),
            org_id=data.get("org_id"),
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_cents=cost_cents,
            success=success,
            error=error,
            started_at=now,
            completed_at=now,
            created_at=now,
        )

        self.session.add(call)

        # Update pipeline run with provider call reference
        if self._pipeline_run and operation == "llm":
            self._pipeline_run.llm_provider_call_id = call_id
            if tokens_in:
                self._pipeline_run.tokens_in = (
                    (self._pipeline_run.tokens_in or 0) + tokens_in
                )
            if tokens_out:
                self._pipeline_run.tokens_out = (
                    (self._pipeline_run.tokens_out or 0) + tokens_out
                )
            if cost_cents:
                self._pipeline_run.total_cost_cents = (
                    (self._pipeline_run.total_cost_cents or 0) + cost_cents
                )

        return call_id

    async def complete_pipeline_run(
        self,
        success: bool = True,
        error: str | None = None,
        error_code: str | None = None,
        ttft_ms: int | None = None,
        ttfa_ms: int | None = None,
        ttfc_ms: int | None = None,
    ) -> None:
        """Complete the pipeline run.

        Args:
            success: Whether the run succeeded
            error: Error message if failed
            error_code: Error code if failed
            ttft_ms: Time to first token
            ttfa_ms: Time to first audio
            ttfc_ms: Time to first chunk
        """
        if not self._pipeline_run:
            return

        now = datetime.now(UTC)
        self._pipeline_run.success = success
        self._pipeline_run.error = error
        self._pipeline_run.error_code = error_code
        self._pipeline_run.completed_at = now
        self._pipeline_run.ttft_ms = ttft_ms
        self._pipeline_run.ttfa_ms = ttfa_ms
        self._pipeline_run.ttfc_ms = ttfc_ms

        # Calculate total latency
        if self._pipeline_run.started_at:
            delta = now - self._pipeline_run.started_at
            self._pipeline_run.total_latency_ms = int(delta.total_seconds() * 1000)

        await self.session.flush()

        logger.debug(
            "Pipeline run completed",
            extra={
                "pipeline_run_id": str(self._pipeline_run_id),
                "success": success,
                "total_latency_ms": self._pipeline_run.total_latency_ms,
            },
        )

    async def flush(self) -> None:
        """Flush all buffered events to the database."""
        if self._events:
            await self.session.flush()
            self._events.clear()

    @property
    def pipeline_run_id(self) -> UUID | None:
        """Get the current pipeline run ID."""
        return self._pipeline_run_id


class MetricsSink:
    """Prometheus metrics sink for pipeline events.

    Emits metrics for pipeline runs, stages, and provider calls.
    """

    def __init__(self, pipeline_name: str):
        self.pipeline_name = pipeline_name

    async def record_pipeline_completion(
        self,
        success: bool,
        duration_seconds: float,
    ) -> None:
        """Record pipeline run completion.

        Args:
            success: Whether the run succeeded
            duration_seconds: Run duration in seconds
        """
        status = "success" if success else "failure"
        record_pipeline_run(self.pipeline_name, status, duration_seconds)

    async def record_stage_completion(
        self,
        stage_name: str,
        success: bool,
        duration_seconds: float,
    ) -> None:
        """Record stage execution completion.

        Args:
            stage_name: Stage name
            success: Whether the stage succeeded
            duration_seconds: Stage duration in seconds
        """
        status = "success" if success else "failure"
        record_stage_execution(
            self.pipeline_name,
            stage_name,
            status,
            duration_seconds,
        )

    async def record_llm_call(
        self,
        provider: str,
        model: str,
        success: bool,
        duration_seconds: float,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_cents: int = 0,
    ) -> None:
        """Record LLM provider call.

        Args:
            provider: Provider name
            model: Model name
            success: Whether the call succeeded
            duration_seconds: Call duration in seconds
            tokens_in: Input tokens
            tokens_out: Output tokens
            cost_cents: Cost in cents
        """
        status = "success" if success else "failure"
        record_llm_request(
            provider=provider,
            model=model,
            status=status,
            duration_seconds=duration_seconds,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_cents=cost_cents,
        )
