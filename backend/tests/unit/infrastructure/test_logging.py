"""Tests for logging configuration."""

import json
import logging

from app.logging_config import (
    StructuredFormatter,
    clear_request_context,
    get_logger,
    request_id_var,
    session_id_var,
    set_request_context,
    user_id_var,
)


class TestStructuredFormatter:
    """Test StructuredFormatter class."""

    def test_formats_as_json(self):
        """Test that logs are formatted as JSON."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["level"] == "info"
        assert parsed["message"] == "Test message"
        assert parsed["logger"] == "test"
        assert "ts" in parsed

    def test_includes_context_variables(self):
        """Test that context variables are included."""
        formatter = StructuredFormatter()

        # Set context
        request_id_var.set("req_123")
        user_id_var.set("user_456")
        session_id_var.set("sess_789")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["request_id"] == "req_123"
        assert parsed["user_id"] == "user_456"
        assert parsed["session_id"] == "sess_789"

        # Clean up
        clear_request_context()

    def test_includes_extra_fields(self):
        """Test that extra fields are included."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.service = "auth"
        record.duration_ms = 100

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["service"] == "auth"
        assert parsed["duration_ms"] == 100


class TestContextFunctions:
    """Test context management functions."""

    def test_set_and_clear_context(self):
        """Test setting and clearing request context."""
        clear_request_context()

        # Initially None
        assert request_id_var.get() is None
        assert user_id_var.get() is None
        assert session_id_var.get() is None

        # Set values
        set_request_context(
            request_id="req_123",
            user_id="user_456",
            session_id="sess_789",
        )

        assert request_id_var.get() == "req_123"
        assert user_id_var.get() == "user_456"
        assert session_id_var.get() == "sess_789"

        # Clear
        clear_request_context()

        assert request_id_var.get() is None
        assert user_id_var.get() is None
        assert session_id_var.get() is None


class TestNamespaceFilter:
    """Test NamespaceFilter class."""

    def test_allows_info_level(self):
        """Test that INFO+ level logs pass through."""
        from app.logging_config import NamespaceFilter

        filter = NamespaceFilter(debug_namespaces=[])
        record = logging.LogRecord(
            name="any_service",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        assert filter.filter(record) is True

    def test_filters_debug_by_namespace(self):
        """Test that DEBUG logs are filtered by namespace."""
        from app.logging_config import NamespaceFilter

        filter = NamespaceFilter(debug_namespaces=["ws", "auth"])

        # Should pass - ws namespace enabled
        ws_record = logging.LogRecord(
            name="ws.connection",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        assert filter.filter(ws_record) is True

        # Should NOT pass - db namespace not enabled
        db_record = logging.LogRecord(
            name="db.query",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        assert filter.filter(db_record) is False


class TestGetLogger:
    """Test get_logger function."""

    def test_returns_logger(self):
        """Test that get_logger returns a Logger instance."""
        logger = get_logger("test_service")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_service"
