"""HelloSales Backend API - FastAPI Application."""

import datetime
import logging
import os
import re
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import markdown
from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import case, func, select

from app.ai.substrate.events import clear_event_sink
from app.api.http.account import router as account_router
from app.api.http.auth import router as auth_router
from app.api.http.feedback import router as feedback_router
from app.api.http.legal import router as legal_router
from app.api.http.orgs import router as orgs_router
from app.api.http.profile import router as profile_router
from app.api.http.progress import router as progress_router
from app.api.http.pulse import router as pulse_router
from app.api.http.sailwind import router as sailwind_router
from app.api.ws import websocket_endpoint
from app.config import get_settings
from app.database import close_db, init_db
from app.logging_config import (
    clear_request_context,
    set_request_context,
    setup_logging,
)
from app.models.observability import PipelineEvent, PipelineRun

print(f"DEBUG: app.main loaded from {__file__}")
print(f"DEBUG: Current working directory: {os.getcwd()}")
print(f"DEBUG: Python path: {sys.path}")

# Initialize settings
settings = get_settings()

# Project root (backend/app/main.py -> backend -> project root)
BASE_DIR = Path(__file__).resolve().parents[2]

# Setup logging
setup_logging(
    log_level=settings.log_level,
    debug_namespaces=settings.debug_namespaces,
)

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("Starting HelloSales Backend", extra={"service": "app"})
    settings.log_config_summary()

    # WorkOS is always required for enterprise
    if (
        not settings.is_development
        and not settings.workos_client_id
    ):
        logger.error(
            "WorkOS client_id is required in non-development environments",
            extra={"service": "app"},
        )
        raise RuntimeError("WorkOS is not configured for enterprise environment")

    # Initialize database
    await init_db()

    yield

    # Shutdown
    logger.info("Shutting down HelloSales Backend", extra={"service": "app"})
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="HelloSales API",
    description="Sales Management Platform Backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
def get_allowed_origins() -> list[str]:
    """Get list of allowed CORS origins."""
    origins: list[str] = []

    # Add enterprise mobile app origin
    if settings.mobile_enterprise_origin:
        origins.append(settings.mobile_enterprise_origin)

    # In development, allow all localhost origins
    if settings.is_development:
        origins.append("http://localhost:*")
        origins.append("http://127.0.0.1:*")

    # Add any configured origins
    origins.extend(settings.cors_allow_origins_list)

    return list(set(origins))  # Deduplicate


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else get_allowed_origins(),
    allow_origin_regex=None
    if settings.is_development
    else (settings.cors_allow_origin_regex or None),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(account_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(progress_router)
app.include_router(feedback_router)
app.include_router(legal_router)
app.include_router(orgs_router)
app.include_router(pulse_router)
app.include_router(sailwind_router)


@app.middleware("http")
async def _http_request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id")
    if not request_id:
        request_id = str(uuid4())

    set_request_context(request_id=request_id)
    start = time.time()
    status_code: int | None = None
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration_ms = int((time.time() - start) * 1000)
        logger.info(
            "HTTP request completed",
            extra={
                "service": "http",
                "duration_ms": duration_ms,
                "metadata": {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                },
            },
        )
        clear_request_context()
        clear_event_sink()


# =============================================================================
# Public Legal Document Pages
# =============================================================================


def _render_markdown_page(title: str, filename: str) -> HTMLResponse:
    """Render a markdown file from docs/legal as a very simple HTML page.

    This is intentionally minimal and static: it just reads the file and wraps
    it in a basic HTML template with preformatted text. If the file is missing,
    a 404-style page is returned.
    """

    def _normalize_markdown(src: str) -> str:
        lines = src.splitlines()
        out: list[str] = []

        list_re = re.compile(r"^\s*(?:[-*+]\s+|\d+\.\s+)")
        for _i, line in enumerate(lines):
            if list_re.match(line):
                prev = out[-1] if out else ""
                prev_stripped = prev.strip()

                # If a list starts immediately after a paragraph line, most markdown
                # renderers require an empty line for consistent output.
                if prev_stripped and not list_re.match(prev) and not prev_stripped.startswith(">"):
                    out.append("")

            out.append(line)

        # Preserve trailing newline if present.
        normalized = "\n".join(out)
        if src.endswith("\n"):
            normalized += "\n"
        return normalized

    legal_path = BASE_DIR / "docs" / "legal" / filename
    if not legal_path.exists():
        html = f"""<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <title>{title}</title>
  </head>
  <body>
    <h1>{title}</h1>
    <p>Document not found.</p>
  </body>
</html>"""
        return HTMLResponse(content=html, status_code=404)

    content = _normalize_markdown(legal_path.read_text(encoding="utf-8"))
    rendered = markdown.markdown(
        content,
        extensions=["extra", "sane_lists", "toc"],
        output_format="html",
    )

    html = f"""<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{title}</title>
  </head>
  <body>
    <h1>{title}</h1>
    <div style=\"max-width: 720px; margin: 2rem auto; font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.5;\">
      {rendered}
    </div>
  </body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/terms", response_class=HTMLResponse)
async def terms_of_service_page() -> HTMLResponse:
    """Public Terms of Service page.

    Backed by docs/legal/terms-of-service-eloquence.md in the repo.
    """

    return _render_markdown_page(
        "Terms of Service",
        "terms-of-service/terms-of-service-eloquence.md",
    )


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy_page() -> HTMLResponse:
    """Public Privacy Policy page.

    Backed by docs/legal/privacy-policy-eloquence.md in the repo.
    """

    return _render_markdown_page(
        "Privacy Policy",
        "privacy-policy/privacy-policy-eloquence.md",
    )


@app.get("/dpa", response_class=HTMLResponse)
async def data_processing_agreement_page() -> HTMLResponse:
    """Public Data Processing Agreement page.

    Backed by docs/legal/data-processing-agreement.md in the repo.
    """

    return _render_markdown_page(
        "Data Processing Agreement",
        "data-processing-agreement/data-processing-agreement.md",
    )


# =============================================================================
# Health Check Endpoints
# =============================================================================


@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "hellosales-backend"}


@app.get("/health/ready")
async def readiness_check():
    """Readiness check for deployments (checks DB and Redis)."""
    from sqlalchemy import text

    from app.database import get_session_context

    errors = []

    # Check database
    try:
        async with get_session_context() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        errors.append(f"Database: {e}")

    # TODO: Check Redis when implemented

    if errors:
        return {
            "status": "unhealthy",
            "errors": errors,
        }

    return {"status": "ready"}


def _prom_metric_line(name: str, value: int | float, labels: dict[str, str] | None = None) -> str:
    if not labels:
        return f"{name} {value}"

    label_str = ",".join([f'{k}="{v}"' for k, v in labels.items()])
    return f"{name}{{{label_str}}} {value}"


@app.get("/metrics")
async def metrics() -> Response:
    if not settings.prometheus_metrics_enabled:
        raise HTTPException(status_code=404, detail="metrics disabled")

    now = datetime.datetime.utcnow()
    since = now - datetime.timedelta(hours=24)

    bucket_bounds_ms = [250, 500, 1000, 2000, 5000]
    bucket_labels = [str(b) for b in bucket_bounds_ms] + ["+Inf"]

    lines: list[str] = []

    lines.append(
        "# HELP eloquence_pipeline_runs_last_24h Pipeline run counts over the last 24 hours"
    )
    lines.append("# TYPE eloquence_pipeline_runs_last_24h gauge")

    lines.append(
        "# HELP eloquence_pipeline_run_latency_ms_last_24h Pipeline run total latency histogram (ms) over the last 24 hours"
    )
    lines.append("# TYPE eloquence_pipeline_run_latency_ms_last_24h histogram")

    lines.append(
        "# HELP eloquence_llm_ttft_ms_p50_last_24h LLM time-to-first-token p50 (ms) over the last 24 hours"
    )
    lines.append("# TYPE eloquence_llm_ttft_ms_p50_last_24h gauge")
    lines.append(
        "# HELP eloquence_llm_ttft_ms_p95_last_24h LLM time-to-first-token p95 (ms) over the last 24 hours"
    )
    lines.append("# TYPE eloquence_llm_ttft_ms_p95_last_24h gauge")
    lines.append(
        "# HELP eloquence_llm_ttfc_ms_p50_last_24h LLM time-to-first-chunk-for-TTS p50 (ms) over the last 24 hours"
    )
    lines.append("# TYPE eloquence_llm_ttfc_ms_p50_last_24h gauge")
    lines.append(
        "# HELP eloquence_llm_ttfc_ms_p95_last_24h LLM time-to-first-chunk-for-TTS p95 (ms) over the last 24 hours"
    )
    lines.append("# TYPE eloquence_llm_ttfc_ms_p95_last_24h gauge")
    lines.append(
        "# HELP eloquence_llm_ttft_samples_last_24h Sample count for TTFT metrics over the last 24 hours"
    )
    lines.append("# TYPE eloquence_llm_ttft_samples_last_24h gauge")
    lines.append(
        "# HELP eloquence_llm_ttfc_samples_last_24h Sample count for TTFC metrics over the last 24 hours"
    )
    lines.append("# TYPE eloquence_llm_ttfc_samples_last_24h gauge")
    lines.append(
        "# HELP eloquence_llm_tokens_in_avg_last_24h Average prompt token count (estimate) over the last 24 hours"
    )
    lines.append("# TYPE eloquence_llm_tokens_in_avg_last_24h gauge")
    lines.append(
        "# HELP eloquence_llm_tokens_out_avg_last_24h Average output token count (estimate) over the last 24 hours"
    )
    lines.append("# TYPE eloquence_llm_tokens_out_avg_last_24h gauge")

    lines.append(
        "# HELP eloquence_ws_disconnects_total WebSocket disconnect count since process start"
    )
    lines.append("# TYPE eloquence_ws_disconnects_total counter")

    lines.append(
        "# HELP eloquence_ws_emits_total WebSocket message emissions by type since process start"
    )
    lines.append("# TYPE eloquence_ws_emits_total counter")

    lines.append(
        "# HELP eloquence_ws_contract_violations_total WebSocket contract violation counts since process start"
    )
    lines.append("# TYPE eloquence_ws_contract_violations_total counter")

    lines.append(
        "# HELP eloquence_provider_call_attempts_last_24h Provider call attempts (provider.call.started) over the last 24 hours"
    )
    lines.append("# TYPE eloquence_provider_call_attempts_last_24h gauge")
    lines.append(
        "# HELP eloquence_provider_call_failures_last_24h Provider call failures (provider.call.failed) over the last 24 hours"
    )
    lines.append("# TYPE eloquence_provider_call_failures_last_24h gauge")
    lines.append(
        "# HELP eloquence_provider_error_rate_last_24h Provider call error rate (failed/started) over the last 24 hours"
    )
    lines.append("# TYPE eloquence_provider_error_rate_last_24h gauge")

    lines.append(
        "# HELP eloquence_circuit_opened_last_24h Circuit breaker opened events over the last 24 hours"
    )
    lines.append("# TYPE eloquence_circuit_opened_last_24h gauge")

    from app.database import get_session_context

    async with get_session_context() as session:
        status_rows = await session.execute(
            select(
                PipelineRun.service,
                func.count(PipelineRun.id).filter(PipelineRun.success.is_(True)).label("success"),
                func.count(PipelineRun.id).filter(PipelineRun.success.is_(False)).label("failed"),
                func.count(PipelineRun.id).filter(PipelineRun.success.is_(None)).label("unknown"),
            )
            .where(PipelineRun.created_at >= since)
            .group_by(PipelineRun.service)
            .order_by(PipelineRun.service)
        )

        for svc, success_count, failed_count, unknown_count in status_rows.all():
            service = str(svc)
            lines.append(
                _prom_metric_line(
                    "eloquence_pipeline_runs_last_24h",
                    int(success_count or 0),
                    {"status": "success", "service": service},
                )
            )

            lines.append(
                _prom_metric_line(
                    "eloquence_pipeline_runs_last_24h",
                    int(failed_count or 0),
                    {"status": "failed", "service": service},
                )
            )
            lines.append(
                _prom_metric_line(
                    "eloquence_pipeline_runs_last_24h",
                    int(unknown_count or 0),
                    {"status": "unknown", "service": service},
                )
            )

        bucket_expr = case(
            (PipelineRun.total_latency_ms < bucket_bounds_ms[0], f"0-{bucket_bounds_ms[0]}"),
            (
                PipelineRun.total_latency_ms < bucket_bounds_ms[1],
                f"{bucket_bounds_ms[0]}-{bucket_bounds_ms[1]}",
            ),
            (
                PipelineRun.total_latency_ms < bucket_bounds_ms[2],
                f"{bucket_bounds_ms[1]}-{bucket_bounds_ms[2]}",
            ),
            (
                PipelineRun.total_latency_ms < bucket_bounds_ms[3],
                f"{bucket_bounds_ms[2]}-{bucket_bounds_ms[3]}",
            ),
            (
                PipelineRun.total_latency_ms < bucket_bounds_ms[4],
                f"{bucket_bounds_ms[3]}-{bucket_bounds_ms[4]}",
            ),
            else_=f"{bucket_bounds_ms[4]}+",
        ).label("bucket")

        hist_rows = await session.execute(
            select(
                PipelineRun.service,
                bucket_expr,
                func.count(PipelineRun.id).label("count"),
                func.sum(PipelineRun.total_latency_ms).label("sum_ms"),
            )
            .where(
                PipelineRun.created_at >= since,
                PipelineRun.total_latency_ms.is_not(None),
            )
            .group_by(PipelineRun.service, bucket_expr)
        )

        provider_expr = func.jsonb_extract_path_text(PipelineRun.stages, "llm", "provider")
        model_expr = func.jsonb_extract_path_text(PipelineRun.stages, "llm", "model")
        ttft_rows = await session.execute(
            select(
                PipelineRun.service,
                PipelineRun.quality_mode,
                provider_expr.label("provider"),
                model_expr.label("model"),
                func.count(PipelineRun.id).label("count"),
                func.percentile_cont(0.5).within_group(PipelineRun.ttft_ms).label("p50"),
                func.percentile_cont(0.95).within_group(PipelineRun.ttft_ms).label("p95"),
                func.avg(PipelineRun.tokens_in).label("avg_tokens_in"),
                func.avg(PipelineRun.tokens_out).label("avg_tokens_out"),
            )
            .where(
                PipelineRun.created_at >= since,
                PipelineRun.ttft_ms.is_not(None),
            )
            .group_by(PipelineRun.service, PipelineRun.quality_mode, provider_expr, model_expr)
        )

        provider_call_operation_expr = func.jsonb_extract_path_text(PipelineEvent.data, "operation")
        provider_call_provider_expr = func.jsonb_extract_path_text(PipelineEvent.data, "provider")
        provider_call_model_expr = func.jsonb_extract_path_text(PipelineEvent.data, "model_id")

        provider_call_rows = await session.execute(
            select(
                provider_call_operation_expr.label("operation"),
                provider_call_provider_expr.label("provider"),
                provider_call_model_expr.label("model_id"),
                func.count(PipelineEvent.id)
                .filter(PipelineEvent.type == "provider.call.started")
                .label("started"),
                func.count(PipelineEvent.id)
                .filter(PipelineEvent.type == "provider.call.failed")
                .label("failed"),
            )
            .where(
                PipelineEvent.timestamp >= since,
                PipelineEvent.type.in_(["provider.call.started", "provider.call.failed"]),
            )
            .group_by(
                provider_call_operation_expr,
                provider_call_provider_expr,
                provider_call_model_expr,
            )
            .order_by(
                provider_call_operation_expr,
                provider_call_provider_expr,
                provider_call_model_expr,
            )
        )

        for operation, provider, model_id, started, failed in provider_call_rows.all():
            labels = {
                "operation": str(operation) if operation is not None else "unknown",
                "provider": str(provider) if provider is not None else "unknown",
                "model_id": str(model_id) if model_id is not None else "unknown",
            }
            started_count = int(started or 0)
            failed_count = int(failed or 0)

            lines.append(
                _prom_metric_line(
                    "eloquence_provider_call_attempts_last_24h",
                    started_count,
                    labels,
                )
            )
            lines.append(
                _prom_metric_line(
                    "eloquence_provider_call_failures_last_24h",
                    failed_count,
                    labels,
                )
            )
            if started_count > 0:
                lines.append(
                    _prom_metric_line(
                        "eloquence_provider_error_rate_last_24h",
                        float(failed_count) / float(started_count),
                        labels,
                    )
                )

        circuit_operation_expr = func.jsonb_extract_path_text(PipelineEvent.data, "operation")
        circuit_provider_expr = func.jsonb_extract_path_text(PipelineEvent.data, "provider")
        circuit_open_rows = await session.execute(
            select(
                circuit_operation_expr.label("operation"),
                circuit_provider_expr.label("provider"),
                func.count(PipelineEvent.id).label("count"),
            )
            .where(
                PipelineEvent.timestamp >= since,
                PipelineEvent.type == "circuit.opened",
            )
            .group_by(
                circuit_operation_expr,
                circuit_provider_expr,
            )
            .order_by(
                circuit_operation_expr,
                circuit_provider_expr,
            )
        )

        for operation, provider, count in circuit_open_rows.all():
            labels = {
                "operation": str(operation) if operation is not None else "unknown",
                "provider": str(provider) if provider is not None else "unknown",
            }
            lines.append(
                _prom_metric_line(
                    "eloquence_circuit_opened_last_24h",
                    int(count or 0),
                    labels,
                )
            )

        ttfc_rows = await session.execute(
            select(
                PipelineRun.service,
                PipelineRun.quality_mode,
                provider_expr.label("provider"),
                model_expr.label("model"),
                func.count(PipelineRun.id).label("count"),
                func.percentile_cont(0.5).within_group(PipelineRun.ttfc_ms).label("p50"),
                func.percentile_cont(0.95).within_group(PipelineRun.ttfc_ms).label("p95"),
            )
            .where(
                PipelineRun.created_at >= since,
                PipelineRun.ttfc_ms.is_not(None),
            )
            .group_by(PipelineRun.service, PipelineRun.quality_mode, provider_expr, model_expr)
        )

        per_service_bucket: dict[str, dict[str, int]] = {}
        per_service_sum: dict[str, int] = {}
        per_service_count: dict[str, int] = {}

        for svc, bucket, count, sum_ms in hist_rows.all():
            service = str(svc)
            per_service_bucket.setdefault(service, {})
            per_service_bucket[service][str(bucket)] = int(count or 0)
            per_service_sum[service] = per_service_sum.get(service, 0) + int(sum_ms or 0)
            per_service_count[service] = per_service_count.get(service, 0) + int(count or 0)

        bucket_order = [
            f"0-{bucket_bounds_ms[0]}",
            f"{bucket_bounds_ms[0]}-{bucket_bounds_ms[1]}",
            f"{bucket_bounds_ms[1]}-{bucket_bounds_ms[2]}",
            f"{bucket_bounds_ms[2]}-{bucket_bounds_ms[3]}",
            f"{bucket_bounds_ms[3]}-{bucket_bounds_ms[4]}",
            f"{bucket_bounds_ms[4]}+",
        ]

        for service, bucket_counts in sorted(per_service_bucket.items(), key=lambda x: x[0]):
            cumulative = 0
            for idx, bucket_name in enumerate(bucket_order):
                cumulative += int(bucket_counts.get(bucket_name, 0))
                lines.append(
                    _prom_metric_line(
                        "eloquence_pipeline_run_latency_ms_last_24h_bucket",
                        cumulative,
                        {"le": bucket_labels[idx], "service": service},
                    )
                )

            total_count = int(per_service_count.get(service, 0))
            lines.append(
                _prom_metric_line(
                    "eloquence_pipeline_run_latency_ms_last_24h_bucket",
                    total_count,
                    {"le": "+Inf", "service": service},
                )
            )
            lines.append(
                _prom_metric_line(
                    "eloquence_pipeline_run_latency_ms_last_24h_sum",
                    int(per_service_sum.get(service, 0)),
                    {"service": service},
                )
            )
            lines.append(
                _prom_metric_line(
                    "eloquence_pipeline_run_latency_ms_last_24h_count",
                    total_count,
                    {"service": service},
                )
            )

        for (
            svc,
            quality_mode,
            provider,
            model,
            count,
            p50,
            p95,
            avg_tokens_in,
            avg_tokens_out,
        ) in ttft_rows.all():
            labels = {
                "service": str(svc) if svc is not None else "unknown",
                "quality_mode": str(quality_mode) if quality_mode is not None else "unknown",
                "provider": str(provider) if provider is not None else "unknown",
                "model": str(model) if model is not None else "unknown",
            }

            if p50 is not None:
                lines.append(
                    _prom_metric_line(
                        "eloquence_llm_ttft_ms_p50_last_24h",
                        float(p50),
                        labels,
                    )
                )
            if p95 is not None:
                lines.append(
                    _prom_metric_line(
                        "eloquence_llm_ttft_ms_p95_last_24h",
                        float(p95),
                        labels,
                    )
                )
            lines.append(
                _prom_metric_line(
                    "eloquence_llm_ttft_samples_last_24h",
                    int(count or 0),
                    labels,
                )
            )
            if avg_tokens_in is not None:
                lines.append(
                    _prom_metric_line(
                        "eloquence_llm_tokens_in_avg_last_24h",
                        float(avg_tokens_in),
                        labels,
                    )
                )
            if avg_tokens_out is not None:
                lines.append(
                    _prom_metric_line(
                        "eloquence_llm_tokens_out_avg_last_24h",
                        float(avg_tokens_out),
                        labels,
                    )
                )

        for (
            svc,
            quality_mode,
            provider,
            model,
            count,
            p50,
            p95,
        ) in ttfc_rows.all():
            labels = {
                "service": str(svc) if svc is not None else "unknown",
                "quality_mode": str(quality_mode) if quality_mode is not None else "unknown",
                "provider": str(provider) if provider is not None else "unknown",
                "model": str(model) if model is not None else "unknown",
            }

            if p50 is not None:
                lines.append(
                    _prom_metric_line(
                        "eloquence_llm_ttfc_ms_p50_last_24h",
                        float(p50),
                        labels,
                    )
                )
            if p95 is not None:
                lines.append(
                    _prom_metric_line(
                        "eloquence_llm_ttfc_ms_p95_last_24h",
                        float(p95),
                        labels,
                    )
                )
            lines.append(
                _prom_metric_line(
                    "eloquence_llm_ttfc_samples_last_24h",
                    int(count or 0),
                    labels,
                )
            )

    from app.api.ws.manager import get_connection_manager

    ws_metrics = get_connection_manager().get_metrics_snapshot()
    lines.append(
        _prom_metric_line("eloquence_ws_disconnects_total", ws_metrics["disconnect_count"])
    )

    for msg_type, count in sorted((ws_metrics.get("emit_counts") or {}).items()):
        lines.append(
            _prom_metric_line(
                "eloquence_ws_emits_total",
                int(count),
                {"type": str(msg_type)},
            )
        )

    violation_counts = ws_metrics.get("contract_violation_counts") or {}
    for key in ("missing_chat_complete", "duplicate_chat_complete"):
        lines.append(
            _prom_metric_line(
                "eloquence_ws_contract_violations_total",
                int(violation_counts.get(key, 0)),
                {"type": key},
            )
        )

    body = "\n".join(lines) + "\n"
    return Response(content=body, media_type="text/plain; version=0.0.4")


# =============================================================================
# WebSocket Endpoint
# =============================================================================


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication."""
    await websocket_endpoint(websocket)


# =============================================================================
# Development Info
# =============================================================================


if settings.is_development:
    from app.api.http.test import router as test_router

    app.include_router(test_router)

    @app.get("/")
    async def root():
        """Development root endpoint with API info."""
        return {
            "service": "HelloSales Backend",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health",
            "websocket": "/ws",
        }
