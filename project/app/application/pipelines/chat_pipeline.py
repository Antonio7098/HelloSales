"""Chat pipeline - end-to-end chat message processing."""

import time
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.pipelines.stages.base import StageContext, StageResult
from app.application.pipelines.stages.enrich import (
    ProfileEnrichStage,
    SummaryEnrichStage,
)
from app.application.pipelines.stages.guard import (
    GuardConfig,
    InputGuardStage,
    OutputGuardStage,
)
from app.application.pipelines.stages.llm import LLMStage
from app.application.pipelines.stages.persist import PersistStage
from app.config import Settings
from app.infrastructure.providers.llm.groq import GroqProvider
from app.infrastructure.stageflow.interceptors import (
    CircuitBreakerInterceptor,
    MetricsInterceptor,
    TimeoutInterceptor,
    TracingInterceptor,
)
from app.infrastructure.stageflow.sinks import DbPipelineEventSink, MetricsSink
from app.infrastructure.telemetry import get_logger
from app.infrastructure.telemetry.metrics import PIPELINE_ACTIVE

logger = get_logger(__name__)


class ChatPipeline:
    """Orchestrates the chat message processing pipeline.

    Runs stages in the following order:
    1. InputGuard - Validate and sanitize user input
    2. ProfileEnrich - Load product/client/company context
    3. SummaryEnrich - Load conversation history
    4. LLM - Generate response
    5. OutputGuard - Validate LLM output
    6. Persist - Save to database
    """

    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        llm_provider: GroqProvider,
    ):
        self.db = db
        self.settings = settings
        self.llm_provider = llm_provider

        # Initialize stages
        guard_config = GuardConfig(
            max_input_length=10000,
            sanitize_instead_of_block=True,
        )
        self.input_guard = InputGuardStage(guard_config)
        self.profile_enrich = ProfileEnrichStage(db)
        self.summary_enrich = SummaryEnrichStage(
            db,
            always_include_last_n=settings.always_include_last_n,
        )
        self.llm_stage = LLMStage(llm_provider)
        self.output_guard = OutputGuardStage(guard_config)
        self.persist_stage = PersistStage(db, settings.summary_threshold)

        # Initialize interceptors
        self.timeout = TimeoutInterceptor(settings.stage_timeout_ms)
        self.circuit_breaker = CircuitBreakerInterceptor(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            recovery_timeout_seconds=settings.circuit_breaker_open_seconds,
        )
        self.tracing = TracingInterceptor("chat")
        self.metrics = MetricsInterceptor("chat")

        # Initialize sinks
        self.db_sink = DbPipelineEventSink(db)
        self.metrics_sink = MetricsSink("chat")

    async def run(
        self,
        user_input: str,
        session_id: UUID,
        user_id: UUID,
        org_id: UUID | None = None,
        request_id: str | None = None,
        product_id: UUID | None = None,
        client_id: UUID | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> tuple[StageContext, StageResult]:
        """Run the chat pipeline.

        Args:
            user_input: User message
            session_id: Chat session ID
            user_id: User ID
            org_id: Organization ID
            request_id: HTTP request ID for correlation
            product_id: Optional product context
            client_id: Optional client context
            model: LLM model to use
            temperature: LLM temperature
            max_tokens: Maximum response tokens

        Returns:
            Tuple of (context, final_result)
        """
        start_time = time.perf_counter()

        # Build context
        ctx = StageContext(
            request_id=request_id,
            user_id=user_id,
            org_id=org_id,
            session_id=session_id,
            user_input=user_input,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            metadata={
                "product_id": product_id,
                "client_id": client_id,
            },
        )

        # Start pipeline run tracking
        pipeline_run_id = await self.db_sink.start_pipeline_run(
            service="chat",
            request_id=request_id,
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            topology="standard",
        )
        ctx.pipeline_run_id = pipeline_run_id

        PIPELINE_ACTIVE.labels(pipeline_name="chat").inc()

        try:
            # Run stages
            stages = [
                ("input_guard", self.input_guard),
                ("profile_enrich", self.profile_enrich),
                ("summary_enrich", self.summary_enrich),
                ("llm", self.llm_stage),
                ("output_guard", self.output_guard),
                ("persist", self.persist_stage),
            ]

            final_result = StageResult(success=True)

            for stage_name, stage in stages:
                # Check circuit breaker
                if self.circuit_breaker.get_state(stage_name) == "open":
                    logger.warning(
                        f"Stage {stage_name} circuit breaker open, skipping"
                    )
                    continue

                # Run stage with interceptors
                result = await self._run_stage_with_interceptors(
                    stage_name,
                    stage,
                    ctx,
                )

                # Record stage result
                await self.db_sink.record_stage_result(
                    stage_name=stage_name,
                    status="success" if result.success else "failure",
                    latency_ms=result.latency_ms,
                    error=result.error,
                )

                if not result.success:
                    final_result = result
                    if not result.should_continue:
                        break

            # Complete pipeline run
            duration_seconds = time.perf_counter() - start_time
            await self.db_sink.complete_pipeline_run(
                success=final_result.success,
                error=final_result.error,
                error_code=final_result.error_code,
            )
            await self.metrics_sink.record_pipeline_completion(
                final_result.success,
                duration_seconds,
            )

            logger.info(
                "Chat pipeline completed",
                extra={
                    "pipeline_run_id": str(pipeline_run_id),
                    "success": final_result.success,
                    "duration_seconds": round(duration_seconds, 3),
                    "tokens_in": ctx.tokens_in,
                    "tokens_out": ctx.tokens_out,
                },
            )

            return ctx, final_result

        except Exception as e:
            duration_seconds = time.perf_counter() - start_time
            await self.db_sink.complete_pipeline_run(
                success=False,
                error=str(e),
                error_code=type(e).__name__,
            )
            await self.metrics_sink.record_pipeline_completion(False, duration_seconds)

            logger.exception(
                "Chat pipeline failed",
                extra={"pipeline_run_id": str(pipeline_run_id)},
            )

            return ctx, StageResult(
                success=False,
                error=str(e),
                error_code=type(e).__name__,
                should_continue=False,
            )

        finally:
            PIPELINE_ACTIVE.labels(pipeline_name="chat").dec()
            await self.db_sink.flush()

    async def _run_stage_with_interceptors(
        self,
        stage_name: str,
        stage,
        ctx: StageContext,
    ) -> StageResult:
        """Run a stage with all interceptors applied."""

        async def run_stage():
            return await stage.run(ctx)

        try:
            # Apply timeout
            result = await self.timeout.wrap(stage_name, run_stage)

            # Update circuit breaker
            if result.success:
                self.circuit_breaker._record_success(
                    self.circuit_breaker._get_state(stage_name)
                )
            else:
                self.circuit_breaker._record_failure(
                    self.circuit_breaker._get_state(stage_name)
                )

            return result

        except Exception as e:
            self.circuit_breaker._record_failure(
                self.circuit_breaker._get_state(stage_name)
            )
            raise


def create_chat_pipeline(
    db: AsyncSession,
    settings: Settings,
) -> ChatPipeline:
    """Factory function to create a chat pipeline.

    Args:
        db: Database session
        settings: Application settings

    Returns:
        Configured ChatPipeline instance
    """
    llm_provider = GroqProvider(settings)
    return ChatPipeline(db, settings, llm_provider)
