from __future__ import annotations

import pytest

from hello_sales_backend.platform.llm import (
    decide_llm_retry,
    empty_completion_issue,
    provider_error_issue,
)
from hello_sales_backend.shared.errors import app_error


def test_llm_execution_policy_retries_retryable_issue_with_attempts_remaining() -> None:
    issue = empty_completion_issue(
        code="agent.provider.empty_completion",
        message="provider returned no content",
    )

    decision = decide_llm_retry(issue=issue, attempt=1, max_attempts=3)

    assert decision.should_retry is True
    assert decision.next_attempt == 2
    assert decision.remaining_attempts == 2


def test_llm_execution_policy_does_not_retry_non_retryable_issue() -> None:
    exc = app_error(
        "provider rejected the request",
        code="provider.request.invalid",
        category="provider",
        status_code=400,
        retryable=False,
    )
    issue = provider_error_issue(exc)

    decision = decide_llm_retry(issue=issue, attempt=1, max_attempts=3)

    assert decision.should_retry is False
    assert decision.next_attempt is None
    assert decision.remaining_attempts == 2


def test_llm_execution_policy_rejects_invalid_attempt_bounds() -> None:
    issue = empty_completion_issue(
        code="agent.provider.empty_completion",
        message="provider returned no content",
    )

    with pytest.raises(ValueError):
        decide_llm_retry(issue=issue, attempt=0, max_attempts=1)
