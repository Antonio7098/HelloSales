"""Structured JSON logging configuration (infrastructure layer)."""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Context variables for request tracing
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
session_id_var: ContextVar[str | None] = ContextVar("session_id", default=None)
pipeline_run_id_var: ContextVar[str | None] = ContextVar("pipeline_run_id", default=None)
org_id_var: ContextVar[str | None] = ContextVar("org_id", default=None)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Add service from extra or derive from logger name
        log_data["service"] = getattr(record, "service", record.name.split(".")[0])

        # Add context from context variables
        if request_id := request_id_var.get():
            log_data["request_id"] = request_id
        if user_id := user_id_var.get():
            log_data["user_id"] = user_id
        if session_id := session_id_var.get():
            log_data["session_id"] = session_id
        if pipeline_run_id := pipeline_run_id_var.get():
            log_data["pipeline_run_id"] = pipeline_run_id
        if org_id := org_id_var.get():
            log_data["org_id"] = org_id

        # Add extra fields from record
        extra_fields = [
            "request_id",
            "user_id",
            "session_id",
            "pipeline_run_id",
            "org_id",
            "workos_org_id",
            "organization_id",
            "provider",
            "model_id",
            "duration_ms",
            "latency_ms",
            "error_code",
            "error_message",
            "error",
            "tokens_in",
            "tokens_out",
            "cost_cents",
            "operation",
            "status",
            "metadata",
            # LLM-specific extras
            "prompt",  # full prompt payload for Groq
            "system_instruction",  # Gemini system text
            "history",  # Gemini chat history
        ]
        for field in extra_fields:
            if hasattr(record, field) and getattr(record, field) is not None:
                log_data[field] = getattr(record, field)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


class NamespaceFilter(logging.Filter):
    """Filter that enables debug logging for specific namespaces."""

    def __init__(self, debug_namespaces: list[str]):
        super().__init__()
        self.debug_namespaces = set(debug_namespaces)

    def filter(self, record: logging.LogRecord) -> bool:
        """Allow all INFO+ logs, but only DEBUG for enabled namespaces."""
        if record.levelno >= logging.INFO:
            return True
        # For DEBUG level, check if namespace is enabled
        namespace = record.name.split(".")[0]
        return namespace in self.debug_namespaces


def setup_logging(log_level: str = "INFO", debug_namespaces: list[str] | None = None) -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Default log level (DEBUG, INFO, WARNING, ERROR)
        debug_namespaces: List of namespaces to enable DEBUG logging for
    """

    debug_namespaces = debug_namespaces or []

    # Create handler with structured formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    # Add namespace filter
    handler.addFilter(NamespaceFilter(debug_namespaces))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)  # Let filter handle level

    # Set specific loggers to WARNING to reduce noise
    for noisy_logger in ["asyncio", "uvicorn.access", "httpx", "httpcore"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    # Log that logging is configured
    logger = logging.getLogger("logging")
    logger.info(
        "Logging configured",
        extra={
            "service": "logging",
            "log_level": log_level,
            "debug_namespaces": debug_namespaces,
        },
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: Logger name (typically the service/module name)

    Returns:
        Configured logger instance
    """

    return logging.getLogger(name)


# Convenience function to set request context

def set_request_context(
    request_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    pipeline_run_id: str | None = None,
    org_id: str | None = None,
) -> None:
    """Set context variables for request tracing."""

    if request_id is not None:
        request_id_var.set(request_id)
    if user_id is not None:
        user_id_var.set(user_id)
    if session_id is not None:
        session_id_var.set(session_id)
    if pipeline_run_id is not None:
        pipeline_run_id_var.set(pipeline_run_id)
    if org_id is not None:
        org_id_var.set(org_id)


def clear_request_context() -> None:
    """Clear all request context variables."""

    request_id_var.set(None)
    user_id_var.set(None)
    session_id_var.set(None)
    pipeline_run_id_var.set(None)
    org_id_var.set(None)


__all__ = [
    "StructuredFormatter",
    "NamespaceFilter",
    "setup_logging",
    "get_logger",
    "set_request_context",
    "clear_request_context",
    "request_id_var",
    "user_id_var",
    "session_id_var",
    "pipeline_run_id_var",
    "org_id_var",
]
