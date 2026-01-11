"""Base stage definitions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from app.domain.protocols.providers import LLMMessage


@dataclass
class StageContext:
    """Context passed through pipeline stages.

    Contains all data needed for pipeline execution,
    accumulated through stage processing.
    """

    # Request identification
    request_id: str | None = None
    pipeline_run_id: UUID | None = None

    # User context
    user_id: UUID | None = None
    org_id: UUID | None = None
    session_id: UUID | None = None

    # Input data
    user_input: str = ""
    input_type: str = "text"  # text, audio

    # Messages for LLM
    messages: list[LLMMessage] = field(default_factory=list)

    # Enrichment data
    system_prompt: str = ""
    product_context: dict[str, Any] = field(default_factory=dict)
    client_context: dict[str, Any] = field(default_factory=dict)
    company_context: dict[str, Any] = field(default_factory=dict)
    conversation_summary: str | None = None
    recent_turns: list[LLMMessage] = field(default_factory=list)

    # LLM configuration
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 1024

    # Output data
    llm_response: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0

    # Guard data
    input_blocked: bool = False
    input_block_reason: str | None = None
    output_blocked: bool = False
    output_block_reason: str | None = None
    sanitized_output: str | None = None

    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Custom metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_final_output(self) -> str:
        """Get the final output, applying sanitization if blocked."""
        if self.output_blocked and self.sanitized_output:
            return self.sanitized_output
        return self.llm_response or ""

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation."""
        self.messages.append(LLMMessage(role=role, content=content))

    def set_system_message(self, content: str) -> None:
        """Set or update the system message."""
        # Remove existing system message if any
        self.messages = [m for m in self.messages if m.role != "system"]
        # Add new system message at the beginning
        self.messages.insert(0, LLMMessage(role="system", content=content))


@dataclass
class StageResult:
    """Result of a stage execution."""

    success: bool = True
    error: str | None = None
    error_code: str | None = None
    should_continue: bool = True  # Whether to continue pipeline
    latency_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


T = TypeVar("T", bound=StageContext)


class Stage(ABC, Generic[T]):
    """Base class for pipeline stages.

    Each stage receives a context, processes it, and returns
    a result indicating success/failure.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Stage name for logging and metrics."""
        ...

    @abstractmethod
    async def execute(self, ctx: T) -> StageResult:
        """Execute the stage.

        Args:
            ctx: Pipeline context

        Returns:
            Stage result
        """
        ...

    async def before_execute(self, ctx: T) -> None:
        """Hook called before execute.

        Override for pre-processing logic.
        """
        pass

    async def after_execute(self, ctx: T, result: StageResult) -> None:
        """Hook called after execute.

        Override for post-processing logic.
        """
        pass

    async def run(self, ctx: T) -> StageResult:
        """Run the stage with before/after hooks.

        Args:
            ctx: Pipeline context

        Returns:
            Stage result
        """
        import time

        start = time.perf_counter()

        try:
            await self.before_execute(ctx)
            result = await self.execute(ctx)
            await self.after_execute(ctx, result)

            result.latency_ms = int((time.perf_counter() - start) * 1000)
            return result

        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            return StageResult(
                success=False,
                error=str(e),
                error_code=type(e).__name__,
                should_continue=False,
                latency_ms=latency_ms,
            )
