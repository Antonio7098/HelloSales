"""Structured logging with context injection."""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Context variables for correlation IDs
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
org_id_var: ContextVar[str | None] = ContextVar("org_id", default=None)
session_id_var: ContextVar[str | None] = ContextVar("session_id", default=None)
pipeline_run_id_var: ContextVar[str | None] = ContextVar("pipeline_run_id", default=None)


def set_request_context(
    request_id: str | None = None,
    user_id: str | None = None,
    org_id: str | None = None,
    session_id: str | None = None,
    pipeline_run_id: str | None = None,
) -> None:
    """Set context variables for request correlation."""
    if request_id is not None:
        request_id_var.set(request_id)
    if user_id is not None:
        user_id_var.set(user_id)
    if org_id is not None:
        org_id_var.set(org_id)
    if session_id is not None:
        session_id_var.set(session_id)
    if pipeline_run_id is not None:
        pipeline_run_id_var.set(pipeline_run_id)


def clear_request_context() -> None:
    """Clear all context variables."""
    request_id_var.set(None)
    user_id_var.set(None)
    org_id_var.set(None)
    session_id_var.set(None)
    pipeline_run_id_var.set(None)


class StructuredFormatter(logging.Formatter):
    """JSON formatter with automatic context injection."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add correlation IDs from context
        if request_id := request_id_var.get():
            log_data["request_id"] = request_id
        if user_id := user_id_var.get():
            log_data["user_id"] = user_id
        if org_id := org_id_var.get():
            log_data["org_id"] = org_id
        if session_id := session_id_var.get():
            log_data["session_id"] = session_id
        if pipeline_run_id := pipeline_run_id_var.get():
            log_data["pipeline_run_id"] = pipeline_run_id

        # Add exception info if present
        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_data.update(record.extra)

        # Filter out None values
        log_data = {k: v for k, v in log_data.items() if v is not None}

        return json.dumps(log_data, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter for development."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname
        name = record.name
        message = record.getMessage()

        # Build context string
        context_parts = []
        if request_id := request_id_var.get():
            context_parts.append(f"req={request_id[:8]}")
        if user_id := user_id_var.get():
            context_parts.append(f"user={user_id[:8]}")
        if session_id := session_id_var.get():
            context_parts.append(f"session={session_id[:8]}")

        context_str = f" [{', '.join(context_parts)}]" if context_parts else ""

        base = f"{timestamp} | {level:8} | {name}{context_str} | {message}"

        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)

        return base


class ContextLogger(logging.LoggerAdapter):
    """Logger adapter that supports extra fields."""

    def process(
        self, msg: str, kwargs: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        extra = kwargs.get("extra", {})
        if self.extra:
            extra.update(self.extra)
        kwargs["extra"] = extra

        # Store extra on the record for the formatter
        return msg, kwargs


def configure_logging(
    level: str = "INFO",
    format_type: str = "json",
    service_name: str = "hellosales-backend",
) -> None:
    """Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        format_type: Output format ('json' or 'text')
        service_name: Service name for log identification
    """
    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    # Select formatter
    if format_type == "json":
        formatter = StructuredFormatter()
    else:
        formatter = TextFormatter()

    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper()))

    # Configure specific loggers
    # Reduce noise from external libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if level == "DEBUG" else logging.WARNING
    )


def get_logger(name: str, **extra: Any) -> ContextLogger:
    """Get a context-aware logger.

    Args:
        name: Logger name (usually __name__)
        **extra: Additional fields to include in every log message

    Returns:
        ContextLogger instance
    """
    logger = logging.getLogger(name)
    return ContextLogger(logger, extra)
