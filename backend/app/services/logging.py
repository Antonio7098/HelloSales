"""Structured logging utilities for the application.

This module provides structured logging with JSON output and
context-aware logging capabilities.

Design:
- JSON-structured log output
- Context injection for request-scoped logging
- Log levels with semantic meaning
- Correlation IDs for tracing

Usage:
    from app.services.logging import get_logger

    logger = get_logger(__name__)
    logger.info("user_action", user_id="123", action="login")

    # With context
    logger = get_logger(__name__, context={"request_id": "abc"})
    logger.info("processing_started")
"""
from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime
from functools import lru_cache
from json import dumps
from logging import (
    CRITICAL,
    DEBUG,
    ERROR,
    INFO,
    WARNING,
    Formatter,
    Logger,
    LogRecord,
    StreamHandler,
)
from logging import getLogger as get_logging_logger
from sys import stdout
from typing import Any

# Context for request-scoped logging
_context: ContextVar[dict[str, Any] | None] = ContextVar("log_context", default=None)


class StructuredLogFormatter(Formatter):
    """Formatter that outputs JSON-structured logs."""

    def __init__(
        self,
        include_fields: list[str] | None = None,
        exclude_fields: list[str] | None = None,
    ) -> None:
        """Initialize the formatter.

        Args:
            include_fields: Fields to include (if None, include all)
            exclude_fields: Fields to exclude
        """
        super().__init__()
        self.include_fields = include_fields or []
        self.exclude_fields = exclude_fields or [
            "module",
            "name",
            "exc_info",
            "stack_info",
        ]

    def format(self, record: LogRecord) -> str:
        """Format the log record as JSON.

        Args:
            record: The log record to format

        Returns:
            JSON-formatted log string
        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from the record
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in self.exclude_fields:
                continue
            if self.include_fields and key not in self.include_fields:
                continue
            log_data[key] = self._serialize_value(value)

        # Add context from context var
        ctx = _context.get()
        if ctx:
            log_data["context"] = ctx

        return dumps(log_data, default=str)

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value for JSON output."""
        if isinstance(value, Exception):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        try:
            return value
        except Exception:
            return str(value)


class ContextLogger:
    """Logger that includes context in all log messages."""

    def __init__(
        self,
        logger: Logger,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the context logger.

        Args:
            logger: The underlying logger
            context: Initial context to include
        """
        self._logger = logger
        self._context = context or {}

    def bind(self, **kwargs: Any) -> ContextLogger:
        """Create a new logger with additional bound context.

        Args:
            **kwargs: Context key-value pairs to bind

        Returns:
            New ContextLogger with additional context
        """
        new_context = {**self._context, **kwargs}
        return ContextLogger(self._logger, new_context)

    def set_context(self, **kwargs: Any) -> None:
        """Update the context for this logger instance.

        Args:
            **kwargs: Context key-value pairs to set
        """
        self._context.update(kwargs)

    def _log_with_context(
        self,
        level: int,
        event: str,
        kwargs: dict[str, Any],
    ) -> None:
        """Log with the current context.

        Args:
            level: Log level
            event: Event name (for structured logging)
            kwargs: Additional fields to log
        """
        extra = {"_context": self._context, "event": event}
        for key, value in kwargs.items():
            extra[key] = value
        self._logger.log(level, event, extra=extra)

    def debug(self, event: str, **kwargs: Any) -> None:
        """Log at DEBUG level."""
        self._log_with_context(DEBUG, event, kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        """Log at INFO level."""
        self._log_with_context(INFO, event, kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        """Log at WARNING level."""
        self._log_with_context(WARNING, event, kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        """Log at ERROR level."""
        self._log_with_context(ERROR, event, kwargs)

    def critical(self, event: str, **kwargs: Any) -> None:
        """Log at CRITICAL level."""
        self._log_with_context(CRITICAL, event, kwargs)

    def exception(self, event: str, **kwargs: Any) -> None:
        """Log at ERROR level with exception info."""
        self._log_with_context(ERROR, event, kwargs)
        self._logger.exception(event, **kwargs)


@lru_cache(maxsize=128)
def get_logger(name: str, level: int = INFO) -> ContextLogger:
    """Get a structured logger for a module.

    Args:
        name: Logger name (typically __name__)
        level: Minimum log level

    Returns:
        ContextLogger instance
    """
    logger = get_logging_logger(name)
    logger.setLevel(level)

    # Add structured formatter if not already added
    if not logger.handlers:
        handler = StreamHandler(stdout)
        handler.setFormatter(StructuredLogFormatter())
        logger.addHandler(handler)

    return ContextLogger(logger)


def set_log_level(level: int) -> None:
    """Set the log level for all app loggers.

    Args:
        level: The log level to set
    """
    root_logger = get_logging_logger()
    root_logger.setLevel(level)


def get_context() -> dict[str, Any]:
    """Get the current logging context.

    Returns:
        The current context from the context variable
    """
    return _context.get()


def set_context(context: dict[str, Any]) -> None:
    """Set the logging context for the current context.

    Args:
        context: The context to set
    """
    _context.set(context)


def clear_context() -> None:
    """Clear the logging context."""
    _context.set({})


def bind_context(**kwargs: Any) -> None:
    """Bind additional context to the current context.

    Args:
        **kwargs: Key-value pairs to add to context
    """
    current = _context.get()
    _context.set({**current, **kwargs})


__all__ = [
    "StructuredLogFormatter",
    "ContextLogger",
    "get_logger",
    "set_log_level",
    "get_context",
    "set_context",
    "clear_context",
    "bind_context",
]
