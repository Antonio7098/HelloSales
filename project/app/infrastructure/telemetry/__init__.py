"""Telemetry infrastructure (logging, tracing, metrics)."""

from app.infrastructure.telemetry.logging import (
    ContextLogger,
    clear_request_context,
    configure_logging,
    get_logger,
    org_id_var,
    pipeline_run_id_var,
    request_id_var,
    session_id_var,
    set_request_context,
    user_id_var,
)
from app.infrastructure.telemetry.metrics import (
    record_guard_block,
    record_http_request,
    record_llm_request,
    record_pipeline_run,
    record_stage_execution,
    set_service_info,
)
from app.infrastructure.telemetry.tracing import (
    configure_tracing,
    create_span,
    get_current_span_id,
    get_current_trace_id,
    get_tracer,
    instrument_fastapi,
    instrument_httpx,
    instrument_sqlalchemy,
    record_exception,
    set_span_attributes,
    shutdown_tracing,
)

__all__ = [
    # Logging
    "ContextLogger",
    "configure_logging",
    "get_logger",
    "set_request_context",
    "clear_request_context",
    "request_id_var",
    "user_id_var",
    "org_id_var",
    "session_id_var",
    "pipeline_run_id_var",
    # Tracing
    "configure_tracing",
    "get_tracer",
    "create_span",
    "set_span_attributes",
    "record_exception",
    "get_current_trace_id",
    "get_current_span_id",
    "instrument_fastapi",
    "instrument_httpx",
    "instrument_sqlalchemy",
    "shutdown_tracing",
    # Metrics
    "set_service_info",
    "record_http_request",
    "record_pipeline_run",
    "record_stage_execution",
    "record_llm_request",
    "record_guard_block",
]
