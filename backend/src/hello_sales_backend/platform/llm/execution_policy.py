"""Shared retry policy for provider-backed LLM execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from hello_sales_backend.shared.errors import AppError, normalize_details


class LLMExecutionIssueKind(StrEnum):
    """Stable classification for retry-relevant LLM execution issues."""

    PROVIDER_ERROR = "provider_error"
    EMPTY_COMPLETION = "empty_completion"
    TIMEOUT = "timeout"
    INVALID_JSON = "invalid_json"
    OUTPUT_VALIDATION = "output_validation"


@dataclass(slots=True, frozen=True)
class LLMExecutionIssue:
    """One normalized issue evaluated by the shared retry policy."""

    kind: LLMExecutionIssueKind
    code: str
    message: str
    retryable: bool
    details: dict[str, Any] = field(default_factory=dict)
    retry_prompt_message: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", normalize_details(self.details))


@dataclass(slots=True, frozen=True)
class LLMRetryDecision:
    """Decision returned by the shared retry policy."""

    issue: LLMExecutionIssue
    attempt: int
    max_attempts: int
    should_retry: bool

    @property
    def remaining_attempts(self) -> int:
        return max(self.max_attempts - self.attempt, 0)

    @property
    def next_attempt(self) -> int | None:
        if not self.should_retry:
            return None
        return self.attempt + 1


def decide_llm_retry(
    *,
    issue: LLMExecutionIssue,
    attempt: int,
    max_attempts: int,
) -> LLMRetryDecision:
    """Return the bounded retry decision for one execution issue."""

    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if attempt > max_attempts:
        raise ValueError("attempt cannot exceed max_attempts")
    return LLMRetryDecision(
        issue=issue,
        attempt=attempt,
        max_attempts=max_attempts,
        should_retry=issue.retryable and attempt < max_attempts,
    )


def provider_error_issue(
    exc: AppError,
    *,
    retryable: bool | None = None,
    details: dict[str, Any] | None = None,
) -> LLMExecutionIssue:
    """Normalize a provider error for policy evaluation."""

    merged_details = dict(exc.details)
    if details:
        merged_details.update(details)
    return LLMExecutionIssue(
        kind=LLMExecutionIssueKind.PROVIDER_ERROR,
        code=exc.code,
        message=exc.message,
        retryable=exc.retryable if retryable is None else retryable,
        details=merged_details,
    )


def timeout_issue(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> LLMExecutionIssue:
    """Normalize a timeout for policy evaluation."""

    return LLMExecutionIssue(
        kind=LLMExecutionIssueKind.TIMEOUT,
        code=code,
        message=message,
        retryable=True,
        details=details or {},
    )


def empty_completion_issue(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    retry_prompt_message: str | None = None,
) -> LLMExecutionIssue:
    """Normalize an empty provider completion for policy evaluation."""

    return LLMExecutionIssue(
        kind=LLMExecutionIssueKind.EMPTY_COMPLETION,
        code=code,
        message=message,
        retryable=True,
        details=details or {},
        retry_prompt_message=retry_prompt_message,
    )


def invalid_json_issue(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> LLMExecutionIssue:
    """Normalize a non-JSON provider result for policy evaluation."""

    return LLMExecutionIssue(
        kind=LLMExecutionIssueKind.INVALID_JSON,
        code=code,
        message=message,
        retryable=True,
        details=details or {},
    )


def output_validation_issue(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> LLMExecutionIssue:
    """Normalize a local output validation failure for policy evaluation."""

    return LLMExecutionIssue(
        kind=LLMExecutionIssueKind.OUTPUT_VALIDATION,
        code=code,
        message=message,
        retryable=True,
        details=details or {},
    )
