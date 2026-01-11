"""Stageflow interceptors for cross-cutting concerns."""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Coroutine, TypeVar

from app.infrastructure.telemetry import create_span, get_logger, set_span_attributes

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class CircuitBreakerState:
    """Circuit breaker state tracking."""

    failures: int = 0
    last_failure_time: datetime | None = None
    state: str = "closed"  # closed, open, half-open
    opened_at: datetime | None = None


class TimeoutInterceptor:
    """Enforces timeout on stage execution.

    Wraps stage execution with an asyncio timeout.
    """

    def __init__(self, timeout_ms: int = 30000):
        """Initialize timeout interceptor.

        Args:
            timeout_ms: Timeout in milliseconds
        """
        self.timeout_seconds = timeout_ms / 1000.0

    async def wrap(
        self,
        stage_name: str,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Wrap a function with timeout.

        Args:
            stage_name: Name of the stage for logging
            func: Async function to wrap
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            asyncio.TimeoutError: If timeout exceeded
        """
        try:
            return await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Stage execution timed out",
                extra={
                    "stage": stage_name,
                    "timeout_ms": int(self.timeout_seconds * 1000),
                },
            )
            raise


class CircuitBreakerInterceptor:
    """Circuit breaker pattern for stage execution.

    Opens circuit after consecutive failures, preventing
    cascade failures and allowing recovery.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout_seconds: int = 60,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout_seconds: Seconds before half-open
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout_seconds)
        self._states: dict[str, CircuitBreakerState] = defaultdict(CircuitBreakerState)

    def _get_state(self, name: str) -> CircuitBreakerState:
        """Get circuit breaker state for a name."""
        return self._states[name]

    def _should_allow(self, state: CircuitBreakerState) -> bool:
        """Check if request should be allowed."""
        if state.state == "closed":
            return True

        if state.state == "open":
            # Check if recovery timeout has passed
            if state.opened_at and datetime.now(UTC) - state.opened_at >= self.recovery_timeout:
                state.state = "half-open"
                return True
            return False

        # half-open: allow one request
        return True

    def _record_success(self, state: CircuitBreakerState) -> None:
        """Record a successful execution."""
        if state.state == "half-open":
            # Reset to closed on success
            state.state = "closed"
            state.failures = 0
            state.opened_at = None

    def _record_failure(self, state: CircuitBreakerState) -> None:
        """Record a failed execution."""
        state.failures += 1
        state.last_failure_time = datetime.now(UTC)

        if state.failures >= self.failure_threshold:
            state.state = "open"
            state.opened_at = datetime.now(UTC)
            logger.warning(
                "Circuit breaker opened",
                extra={
                    "failures": state.failures,
                    "threshold": self.failure_threshold,
                },
            )

    async def wrap(
        self,
        name: str,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Wrap a function with circuit breaker.

        Args:
            name: Circuit breaker name
            func: Async function to wrap
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            RuntimeError: If circuit is open
        """
        state = self._get_state(name)

        if not self._should_allow(state):
            raise RuntimeError(f"Circuit breaker open for {name}")

        try:
            result = await func(*args, **kwargs)
            self._record_success(state)
            return result
        except Exception:
            self._record_failure(state)
            raise

    def get_state(self, name: str) -> str:
        """Get current circuit state.

        Args:
            name: Circuit breaker name

        Returns:
            State string (closed, open, half-open)
        """
        return self._get_state(name).state

    def reset(self, name: str) -> None:
        """Reset circuit breaker to closed.

        Args:
            name: Circuit breaker name
        """
        self._states[name] = CircuitBreakerState()


class TracingInterceptor:
    """OpenTelemetry tracing for stage execution.

    Creates spans for each stage execution with timing
    and attribute information.
    """

    def __init__(self, pipeline_name: str):
        """Initialize tracing interceptor.

        Args:
            pipeline_name: Name of the pipeline for span naming
        """
        self.pipeline_name = pipeline_name

    async def wrap(
        self,
        stage_name: str,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Wrap a function with tracing.

        Args:
            stage_name: Name of the stage
            func: Async function to wrap
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        with create_span(
            f"{self.pipeline_name}.{stage_name}",
            attributes={
                "pipeline": self.pipeline_name,
                "stage": stage_name,
            },
        ) as span:
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                set_span_attributes({
                    "duration_ms": int((time.perf_counter() - start_time) * 1000),
                    "success": True,
                })
                return result
            except Exception as e:
                set_span_attributes({
                    "duration_ms": int((time.perf_counter() - start_time) * 1000),
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                })
                raise


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay_ms: int = 100
    max_delay_ms: int = 5000
    exponential_base: float = 2.0
    retryable_exceptions: tuple[type[Exception], ...] = field(
        default_factory=lambda: (TimeoutError, ConnectionError)
    )


class RetryInterceptor:
    """Retry with exponential backoff for stage execution.

    Retries failed executions with configurable backoff.
    """

    def __init__(self, config: RetryConfig | None = None):
        """Initialize retry interceptor.

        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        delay_ms = min(
            self.config.base_delay_ms * (self.config.exponential_base ** attempt),
            self.config.max_delay_ms,
        )
        return delay_ms / 1000.0

    def _should_retry(self, exception: Exception) -> bool:
        """Check if exception is retryable."""
        return isinstance(exception, self.config.retryable_exceptions)

    async def wrap(
        self,
        name: str,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Wrap a function with retry logic.

        Args:
            name: Operation name for logging
            func: Async function to wrap
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Last exception if all retries exhausted
        """
        last_exception: Exception | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if not self._should_retry(e) or attempt >= self.config.max_retries:
                    raise

                delay = self._calculate_delay(attempt)
                logger.warning(
                    "Retrying after failure",
                    extra={
                        "name": name,
                        "attempt": attempt + 1,
                        "max_retries": self.config.max_retries,
                        "delay_seconds": delay,
                        "error": str(e),
                    },
                )
                await asyncio.sleep(delay)

        # Should never reach here, but satisfy type checker
        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected retry loop exit")


class MetricsInterceptor:
    """Metrics collection for stage execution.

    Records timing and success/failure metrics.
    """

    def __init__(self, pipeline_name: str):
        """Initialize metrics interceptor.

        Args:
            pipeline_name: Name of the pipeline for metric labels
        """
        self.pipeline_name = pipeline_name

    async def wrap(
        self,
        stage_name: str,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        sink: Any | None = None,
        **kwargs: Any,
    ) -> T:
        """Wrap a function with metrics collection.

        Args:
            stage_name: Name of the stage
            func: Async function to wrap
            *args: Positional arguments
            sink: Optional metrics sink
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        from app.infrastructure.telemetry.metrics import (
            STAGE_DURATION_SECONDS,
            STAGE_EXECUTIONS_TOTAL,
        )

        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            duration = time.perf_counter() - start_time

            STAGE_EXECUTIONS_TOTAL.labels(
                pipeline_name=self.pipeline_name,
                stage_name=stage_name,
                status="success",
            ).inc()
            STAGE_DURATION_SECONDS.labels(
                pipeline_name=self.pipeline_name,
                stage_name=stage_name,
            ).observe(duration)

            if sink:
                await sink.record_stage_completion(stage_name, True, duration)

            return result

        except Exception as e:
            duration = time.perf_counter() - start_time

            STAGE_EXECUTIONS_TOTAL.labels(
                pipeline_name=self.pipeline_name,
                stage_name=stage_name,
                status="failure",
            ).inc()
            STAGE_DURATION_SECONDS.labels(
                pipeline_name=self.pipeline_name,
                stage_name=stage_name,
            ).observe(duration)

            if sink:
                await sink.record_stage_completion(stage_name, False, duration)

            raise
