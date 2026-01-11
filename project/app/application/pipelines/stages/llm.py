"""LLM stage - language model invocation."""

import time

from app.application.pipelines.stages.base import Stage, StageContext, StageResult
from app.domain.errors import ProviderError, ProviderRateLimitError, ProviderTimeoutError
from app.infrastructure.providers.llm.groq import GroqProvider
from app.infrastructure.telemetry import get_logger
from app.infrastructure.telemetry.metrics import record_llm_request

logger = get_logger(__name__)


class LLMStage(Stage[StageContext]):
    """Invokes the LLM to generate a response.

    Handles provider selection, error handling, and
    metrics collection for LLM calls.
    """

    def __init__(self, provider: GroqProvider):
        self.provider = provider

    @property
    def name(self) -> str:
        return "llm"

    async def execute(self, ctx: StageContext) -> StageResult:
        """Execute LLM invocation."""
        if not ctx.messages:
            return StageResult(
                success=False,
                error="No messages to send to LLM",
                error_code="NO_MESSAGES",
                should_continue=False,
            )

        # Skip if input was completely blocked
        if ctx.input_blocked and not ctx.user_input:
            return StageResult(
                success=False,
                error="Input blocked by guard",
                error_code="INPUT_BLOCKED",
                should_continue=False,
            )

        start_time = time.perf_counter()
        model = ctx.model or self.provider.default_model

        try:
            response = await self.provider.chat(
                messages=ctx.messages,
                model=model,
                temperature=ctx.temperature,
                max_tokens=ctx.max_tokens,
            )

            duration_seconds = time.perf_counter() - start_time

            # Update context with response
            ctx.llm_response = response.content
            ctx.tokens_in = response.tokens_in
            ctx.tokens_out = response.tokens_out

            # Calculate cost
            cost_cents = self.provider.calculate_cost_cents(
                response.tokens_in,
                response.tokens_out,
                model,
            )

            # Record metrics
            record_llm_request(
                provider=self.provider.provider_name,
                model=model,
                status="success",
                duration_seconds=duration_seconds,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                cost_cents=cost_cents,
            )

            logger.info(
                "LLM response generated",
                extra={
                    "provider": self.provider.provider_name,
                    "model": model,
                    "tokens_in": response.tokens_in,
                    "tokens_out": response.tokens_out,
                    "cost_cents": cost_cents,
                    "duration_seconds": round(duration_seconds, 3),
                },
            )

            return StageResult(
                success=True,
                metadata={
                    "model": model,
                    "tokens_in": response.tokens_in,
                    "tokens_out": response.tokens_out,
                    "cost_cents": cost_cents,
                    "finish_reason": response.finish_reason,
                },
            )

        except ProviderRateLimitError as e:
            duration_seconds = time.perf_counter() - start_time
            record_llm_request(
                provider=self.provider.provider_name,
                model=model,
                status="rate_limited",
                duration_seconds=duration_seconds,
            )
            logger.warning(
                "LLM rate limited",
                extra={
                    "provider": self.provider.provider_name,
                    "retry_after_seconds": e.retry_after_seconds,
                },
            )
            return StageResult(
                success=False,
                error=str(e),
                error_code="RATE_LIMITED",
                should_continue=False,
                metadata={"retry_after_seconds": e.retry_after_seconds},
            )

        except ProviderTimeoutError as e:
            duration_seconds = time.perf_counter() - start_time
            record_llm_request(
                provider=self.provider.provider_name,
                model=model,
                status="timeout",
                duration_seconds=duration_seconds,
            )
            logger.warning(
                "LLM request timed out",
                extra={"provider": self.provider.provider_name},
            )
            return StageResult(
                success=False,
                error=str(e),
                error_code="TIMEOUT",
                should_continue=False,
            )

        except ProviderError as e:
            duration_seconds = time.perf_counter() - start_time
            record_llm_request(
                provider=self.provider.provider_name,
                model=model,
                status="error",
                duration_seconds=duration_seconds,
            )
            logger.error(
                "LLM provider error",
                extra={
                    "provider": self.provider.provider_name,
                    "error": str(e),
                },
            )
            return StageResult(
                success=False,
                error=str(e),
                error_code="PROVIDER_ERROR",
                should_continue=False,
            )

        except Exception as e:
            duration_seconds = time.perf_counter() - start_time
            record_llm_request(
                provider=self.provider.provider_name,
                model=model,
                status="error",
                duration_seconds=duration_seconds,
            )
            logger.exception(
                "Unexpected LLM error",
                extra={"provider": self.provider.provider_name},
            )
            return StageResult(
                success=False,
                error=str(e),
                error_code="UNEXPECTED_ERROR",
                should_continue=False,
            )
