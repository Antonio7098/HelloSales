from __future__ import annotations

from pydantic import ValidationError

from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.llm import EffectivePromptRef
from hello_sales_backend.platform.observability.metrics import (
    MetricsRuntimeSnapshot,
    NoOpMetricsRuntime,
    PrometheusMetricsRuntime,
)
from hello_sales_backend.platform.observability.telemetry import (
    OpenTelemetryTracingRuntime,
    TracingRuntimeSnapshot,
)


def test_observability_settings_resolve_runtime_metadata() -> None:
    settings = Settings(
        app_name="HelloSales API",
        app_version="1.2.3",
        database_url="sqlite+aiosqlite:///test.db",
    )

    assert settings.resolved_observability_service_name == "HelloSales API"
    assert settings.resolved_observability_service_version == "1.2.3"


def test_observability_settings_validate_metrics_endpoint_path() -> None:
    try:
        Settings(
            database_url="sqlite+aiosqlite:///test.db",
            observability_metrics_endpoint_path="metrics",
        )
    except ValidationError as exc:
        assert "observability_metrics_endpoint_path" in str(exc)
    else:
        raise AssertionError("expected ValidationError for an invalid metrics path")


def test_observability_settings_validate_metrics_exporter() -> None:
    try:
        Settings(
            database_url="sqlite+aiosqlite:///test.db",
            observability_metrics_exporter="statsd",
        )
    except ValidationError as exc:
        assert "observability_metrics_exporter" in str(exc)
    else:
        raise AssertionError("expected ValidationError for an invalid metrics exporter")


def test_observability_settings_validate_tracing_exporter() -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite:///test.db",
        observability_tracing_exporter="otlp",
    )

    assert settings.observability_tracing_exporter == "otlp"


def test_observability_settings_validate_otlp_endpoint() -> None:
    try:
        Settings(
            database_url="sqlite+aiosqlite:///test.db",
            observability_tracing_otlp_endpoint="collector:4318",
        )
    except ValidationError as exc:
        assert "observability_tracing_otlp_endpoint" in str(exc)
    else:
        raise AssertionError("expected ValidationError for an invalid OTLP endpoint")


def test_observability_settings_parse_otlp_headers() -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite:///test.db",
        observability_tracing_otlp_headers="authorization=Bearer test,x-scope-orgid=dev",
    )

    assert settings.resolved_observability_tracing_otlp_headers == {
        "authorization": "Bearer test",
        "x-scope-orgid": "dev",
    }


def test_noop_metrics_runtime_is_safe_when_disabled() -> None:
    runtime = NoOpMetricsRuntime(
        MetricsRuntimeSnapshot(
            enabled=False,
            exporter="prometheus",
            endpoint_enabled=False,
            endpoint_path="/metrics",
            http_enabled=False,
            health_enabled=False,
            background_tasks_enabled=False,
            agents_enabled=False,
        )
    )

    runtime.on_http_request_started()
    runtime.on_http_request_finished(
        method="GET",
        route="/api/system/status",
        status_code=200,
        outcome="success",
        duration_seconds=0.02,
    )
    runtime.observe_health(
        kind="readiness",
        overall_status="ready",
        checks={"database": ("configured", False)},
    )
    runtime.on_background_task_started(purpose="jobs.diagnostic")
    runtime.on_background_task_finished(
        purpose="jobs.diagnostic",
        status="completed",
        duration_seconds=0.1,
    )
    runtime.on_agent_turn_execution_started(profile_name="generic")
    runtime.on_agent_tool_approval_requested(profile_name="generic", tool_name="run_diagnostic_job")
    runtime.on_agent_turn_execution_finished(
        profile_name="generic",
        status="awaiting_approval",
        duration_seconds=0.1,
    )
    runtime.on_agent_tool_call_started(profile_name="generic", tool_name="get_runtime_status")
    runtime.on_agent_tool_call_finished(
        profile_name="generic",
        tool_name="get_runtime_status",
        status="completed",
        duration_seconds=0.1,
    )
    runtime.on_worker_run_started(worker_name="structured-brief", execution_mode="direct")
    runtime.on_worker_run_finished(
        worker_name="structured-brief",
        status="completed",
        duration_seconds=0.1,
    )

    payload, content_type = runtime.render_latest()
    assert payload == b""
    assert content_type.startswith("text/plain")


def test_prometheus_metrics_runtime_renders_expected_metric_families() -> None:
    runtime = PrometheusMetricsRuntime(
        MetricsRuntimeSnapshot(
            enabled=True,
            exporter="prometheus",
            endpoint_enabled=True,
            endpoint_path="/metrics",
            http_enabled=True,
            health_enabled=True,
            background_tasks_enabled=True,
            agents_enabled=True,
            workers_enabled=True,
        )
    )

    runtime.on_http_request_started()
    runtime.on_http_request_finished(
        method="GET",
        route="/api/health/readiness",
        status_code=200,
        outcome="success",
        duration_seconds=0.02,
    )
    runtime.observe_health(
        kind="readiness",
        overall_status="ready",
        checks={"database": ("configured", False), "workflows": ("ok", False)},
    )
    runtime.on_background_task_started(purpose="jobs.diagnostic")
    runtime.on_background_task_finished(
        purpose="jobs.diagnostic",
        status="completed",
        duration_seconds=0.05,
    )
    runtime.on_agent_turn_execution_started(profile_name="generic")
    runtime.on_agent_tool_approval_requested(profile_name="generic", tool_name="run_diagnostic_job")
    runtime.on_agent_turn_execution_finished(
        profile_name="generic",
        status="awaiting_approval",
        duration_seconds=0.04,
    )
    runtime.on_agent_tool_call_started(profile_name="generic", tool_name="get_runtime_status")
    runtime.on_agent_tool_call_finished(
        profile_name="generic",
        tool_name="get_runtime_status",
        status="completed",
        duration_seconds=0.03,
    )
    runtime.on_worker_run_started(worker_name="structured-brief", execution_mode="direct")
    runtime.on_worker_run_finished(
        worker_name="structured-brief",
        status="completed",
        duration_seconds=0.03,
    )

    payload, _ = runtime.render_latest()
    metrics_text = payload.decode("utf-8")
    assert (
        'hello_sales_http_requests_total{method="GET",outcome="success",route="/api/health/readiness",status_code="200"} 1.0'
        in metrics_text
    )
    assert (
        'hello_sales_health_check_status{check="database",kind="readiness",required="false"} 1.0'
        in metrics_text
    )
    assert (
        'hello_sales_background_tasks_completed_total{purpose="jobs.diagnostic",status="completed"} 1.0'
        in metrics_text
    )
    assert (
        'hello_sales_agent_turn_executions_completed_total{profile="generic",status="awaiting_approval"} 1.0'
        in metrics_text
    )
    assert (
        'hello_sales_agent_tool_approval_requests_total{profile="generic",tool="run_diagnostic_job"} 1.0'
        in metrics_text
    )
    assert (
        'hello_sales_agent_tool_calls_completed_total{profile="generic",status="completed",tool="get_runtime_status"} 1.0'
        in metrics_text
    )
    assert (
        'hello_sales_worker_runs_completed_total{status="completed",worker="structured-brief"} 1.0'
        in metrics_text
    )


def test_open_telemetry_runtime_reuses_valid_trace_id_for_spans() -> None:
    trace_id = "0123456789abcdef0123456789abcdef"
    runtime = OpenTelemetryTracingRuntime(
        TracingRuntimeSnapshot(
            enabled=True,
            exporter="none",
            service_name="hello-sales-backend",
            service_version="0.1.0",
            environment="test",
            http_enabled=True,
            background_tasks_enabled=True,
            agents_enabled=True,
            workers_enabled=True,
            otlp_headers={},
        )
    )

    with runtime.start_http_span(
        method="GET",
        path="/api/system/status",
        request_id="req-1",
        trace_id=trace_id,
    ) as http_span:
        assert http_span is not None
        assert f"{http_span.get_span_context().trace_id:032x}" == trace_id

    with runtime.start_background_task_span(
        task_id="task-1",
        purpose="jobs.diagnostic",
        request_id="req-1",
        trace_id=trace_id,
    ) as task_span:
        assert task_span is not None
        assert f"{task_span.get_span_context().trace_id:032x}" == trace_id

    with runtime.start_agent_turn_span(
        run_id="run-1",
        turn_id="turn-1",
        profile_name="generic",
        prompt=EffectivePromptRef(
            prompt_id="agent.generic.response",
            version="v1",
            owner_kind="agent",
            owner_id="generic",
            purpose="response",
        ),
        request_id="req-1",
        trace_id=trace_id,
    ) as agent_turn_span:
        assert agent_turn_span is not None
        assert f"{agent_turn_span.get_span_context().trace_id:032x}" == trace_id

    with runtime.start_agent_tool_span(
        run_id="run-1",
        turn_id="turn-1",
        tool_call_id="tool-1",
        profile_name="generic",
        tool_name="get_runtime_status",
        request_id="req-1",
        trace_id=trace_id,
    ) as agent_tool_span:
        assert agent_tool_span is not None
        assert f"{agent_tool_span.get_span_context().trace_id:032x}" == trace_id

    with runtime.start_worker_run_span(
        run_id="worker-run-1",
        worker_name="structured-brief",
        prompt=EffectivePromptRef(
            prompt_id="worker.structured-brief.generation",
            version="v1",
            owner_kind="worker",
            owner_id="structured-brief",
            purpose="generation",
        ),
        request_id="req-1",
        trace_id=trace_id,
        execution_mode="direct",
    ) as worker_span:
        assert worker_span is not None
        assert f"{worker_span.get_span_context().trace_id:032x}" == trace_id


def test_open_telemetry_runtime_supports_otlp_exporter_configuration() -> None:
    runtime = OpenTelemetryTracingRuntime(
        TracingRuntimeSnapshot(
            enabled=True,
            exporter="otlp",
            service_name="hello-sales-backend",
            service_version="0.1.0",
            environment="test",
            http_enabled=True,
            background_tasks_enabled=True,
            agents_enabled=False,
            workers_enabled=False,
            otlp_endpoint="http://collector.test:4318/v1/traces",
            otlp_headers={"authorization": "Bearer test"},
            otlp_timeout_seconds=3.5,
        )
    )

    assert runtime.snapshot().exporter == "otlp"
    assert runtime.snapshot().otlp_endpoint == "http://collector.test:4318/v1/traces"
    assert runtime.snapshot().otlp_headers == {"authorization": "Bearer test"}
    assert runtime.snapshot().otlp_timeout_seconds == 3.5
