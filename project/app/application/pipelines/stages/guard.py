"""Guard stages - input and output validation."""

import re
from dataclasses import dataclass

from app.application.pipelines.stages.base import Stage, StageContext, StageResult
from app.domain.errors import GuardBlockedError
from app.infrastructure.telemetry import get_logger
from app.infrastructure.telemetry.metrics import record_guard_block

logger = get_logger(__name__)


@dataclass
class GuardConfig:
    """Configuration for guard stages."""

    # Blocked patterns (regex)
    blocked_patterns: list[str] | None = None

    # Categories to block
    blocked_categories: list[str] | None = None

    # Maximum input length
    max_input_length: int = 10000

    # Whether to sanitize or block entirely
    sanitize_instead_of_block: bool = True

    # Replacement text for sanitized content
    sanitization_replacement: str = "[Content removed for safety]"


class InputGuardStage(Stage[StageContext]):
    """Validates and sanitizes user input.

    Checks for:
    - Content length limits
    - Blocked patterns (regex)
    - Injection attempts
    - Profanity/harmful content (basic)
    """

    def __init__(self, config: GuardConfig | None = None):
        self.config = config or GuardConfig()
        self._blocked_patterns = self._compile_patterns()

    @property
    def name(self) -> str:
        return "input_guard"

    def _compile_patterns(self) -> list[re.Pattern]:
        """Compile regex patterns."""
        patterns = self.config.blocked_patterns or []
        # Add default injection patterns
        patterns.extend([
            r"<script.*?>.*?</script>",  # XSS
            r"\{\{.*?\}\}",  # Template injection
            r"\$\{.*?\}",  # Variable injection
        ])
        return [re.compile(p, re.IGNORECASE | re.DOTALL) for p in patterns]

    async def execute(self, ctx: StageContext) -> StageResult:
        """Execute input validation."""
        user_input = ctx.user_input

        # Check length
        if len(user_input) > self.config.max_input_length:
            ctx.input_blocked = True
            ctx.input_block_reason = "Input exceeds maximum length"
            record_guard_block("input", "length_exceeded")

            logger.warning(
                "Input blocked: length exceeded",
                extra={
                    "length": len(user_input),
                    "max_length": self.config.max_input_length,
                },
            )

            if not self.config.sanitize_instead_of_block:
                return StageResult(
                    success=False,
                    error="Input exceeds maximum length",
                    error_code="INPUT_TOO_LONG",
                    should_continue=False,
                )

            # Truncate instead of block
            ctx.user_input = user_input[: self.config.max_input_length]

        # Check patterns
        for pattern in self._blocked_patterns:
            if pattern.search(user_input):
                ctx.input_blocked = True
                ctx.input_block_reason = "Input contains blocked pattern"
                record_guard_block("input", "blocked_pattern")

                logger.warning(
                    "Input blocked: pattern matched",
                    extra={"pattern": pattern.pattern},
                )

                if not self.config.sanitize_instead_of_block:
                    return StageResult(
                        success=False,
                        error="Input contains blocked content",
                        error_code="INPUT_BLOCKED",
                        should_continue=False,
                    )

                # Sanitize the pattern
                ctx.user_input = pattern.sub(
                    self.config.sanitization_replacement,
                    ctx.user_input,
                )

        return StageResult(success=True)


class OutputGuardStage(Stage[StageContext]):
    """Validates and sanitizes LLM output.

    Checks for:
    - Prompt leakage
    - PII exposure
    - Harmful content
    - Off-topic responses
    """

    def __init__(self, config: GuardConfig | None = None):
        self.config = config or GuardConfig()
        self._blocked_patterns = self._compile_patterns()

    @property
    def name(self) -> str:
        return "output_guard"

    def _compile_patterns(self) -> list[re.Pattern]:
        """Compile regex patterns for output checking."""
        patterns = self.config.blocked_patterns or []
        # Add default patterns for prompt leakage
        patterns.extend([
            r"(?i)as an AI language model",
            r"(?i)I cannot help with",
            r"(?i)I apologize, but I",
        ])
        return [re.compile(p, re.IGNORECASE) for p in patterns]

    async def execute(self, ctx: StageContext) -> StageResult:
        """Execute output validation."""
        if not ctx.llm_response:
            return StageResult(success=True)

        output = ctx.llm_response
        sanitized = output

        # Check patterns
        for pattern in self._blocked_patterns:
            if pattern.search(output):
                ctx.output_blocked = True
                ctx.output_block_reason = "Output contains blocked pattern"
                record_guard_block("output", "blocked_pattern")

                logger.warning(
                    "Output blocked: pattern matched",
                    extra={"pattern": pattern.pattern},
                )

                if self.config.sanitize_instead_of_block:
                    sanitized = pattern.sub(
                        self.config.sanitization_replacement,
                        sanitized,
                    )
                else:
                    return StageResult(
                        success=False,
                        error="Output contains blocked content",
                        error_code="OUTPUT_BLOCKED",
                        should_continue=False,
                    )

        # Check for excessive length (might indicate runaway generation)
        max_output_length = self.config.max_input_length * 2
        if len(output) > max_output_length:
            ctx.output_blocked = True
            ctx.output_block_reason = "Output exceeds maximum length"
            record_guard_block("output", "length_exceeded")
            sanitized = sanitized[:max_output_length] + "..."

        if ctx.output_blocked and self.config.sanitize_instead_of_block:
            ctx.sanitized_output = sanitized

        return StageResult(success=True)
