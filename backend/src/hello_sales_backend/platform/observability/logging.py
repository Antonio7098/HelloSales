"""Logging configuration."""

from __future__ import annotations

import logging

import structlog


def configure_logging(level: str, environment: str) -> None:
    """Configure structlog and standard logging."""

    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
    renderer = (
        structlog.processors.JSONRenderer()
        if environment in {"production", "staging"}
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            renderer,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
    )


def get_logger(name: str):
    """Return a configured logger."""

    return structlog.get_logger(name)
