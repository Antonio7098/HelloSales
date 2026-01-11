"""Tests for domain errors."""

import pytest

from app.domain.errors import (
    AppError,
    AuthError,
    GuardBlockedError,
    NotFoundError,
    PipelineCancelledError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    SessionNotFoundError,
    TokenExpiredError,
    ValidationError,
)


class TestAppError:
    """Test base AppError."""

    def test_error_creation(self):
        """Test creating an error."""
        error = AppError(
            code="TEST_ERROR",
            message="Test error message",
            details={"key": "value"},
            retryable=True,
        )

        assert error.code == "TEST_ERROR"
        assert error.message == "Test error message"
        assert error.details == {"key": "value"}
        assert error.retryable is True
        assert error.timestamp is not None

    def test_error_str(self):
        """Test error string representation."""
        error = AppError(code="TEST", message="Test message")
        assert str(error) == "[TEST] Test message"

    def test_error_to_dict(self):
        """Test error serialization."""
        error = AppError(
            code="TEST_ERROR",
            message="Test message",
            details={"key": "value"},
            retryable=False,
        )

        d = error.to_dict()

        assert d["code"] == "TEST_ERROR"
        assert d["message"] == "Test message"
        assert d["details"] == {"key": "value"}
        assert d["retryable"] is False
        assert "timestamp" in d


class TestNotFoundErrors:
    """Test NotFound error variants."""

    def test_session_not_found(self):
        """Test SessionNotFoundError."""
        error = SessionNotFoundError(message="Session not found")

        assert error.code == "SESSION_NOT_FOUND"
        assert error.retryable is False


class TestValidationErrors:
    """Test validation error variants."""

    def test_guard_blocked_error(self):
        """Test GuardBlockedError with extra fields."""
        error = GuardBlockedError(
            message="Content blocked",
            category="profanity",
            blocked_content="***",
        )

        assert error.code == "GUARD_BLOCKED"
        assert error.category == "profanity"
        assert error.blocked_content == "***"
        assert error.retryable is False


class TestAuthErrors:
    """Test auth error variants."""

    def test_token_expired_is_retryable(self):
        """Test that token expired is retryable."""
        error = TokenExpiredError(message="Token expired")

        assert error.code == "TOKEN_EXPIRED"
        assert error.retryable is True


class TestProviderErrors:
    """Test provider error variants."""

    def test_provider_timeout_is_retryable(self):
        """Test that timeout is retryable."""
        error = ProviderTimeoutError(
            message="Timeout",
            provider="groq",
            operation="chat",
        )

        assert error.code == "PROVIDER_TIMEOUT"
        assert error.provider == "groq"
        assert error.operation == "chat"
        assert error.retryable is True

    def test_provider_rate_limit_has_retry_after(self):
        """Test rate limit error has retry info."""
        error = ProviderRateLimitError(
            message="Rate limited",
            provider="groq",
            operation="chat",
            retry_after_seconds=120,
        )

        assert error.code == "PROVIDER_RATE_LIMITED"
        assert error.retry_after_seconds == 120
        assert error.retryable is True


class TestPipelineErrors:
    """Test pipeline error variants."""

    def test_pipeline_cancelled(self):
        """Test pipeline cancelled error."""
        error = PipelineCancelledError(
            message="Pipeline cancelled",
            stage="input_guard",
            pipeline_run_id="run_123",
            cancel_reason="Input blocked",
        )

        assert error.code == "PIPELINE_CANCELLED"
        assert error.stage == "input_guard"
        assert error.pipeline_run_id == "run_123"
        assert error.cancel_reason == "Input blocked"
        assert error.retryable is False
