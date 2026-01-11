"""Prometheus metrics configuration."""

from prometheus_client import Counter, Gauge, Histogram, Info

# Service info
SERVICE_INFO = Info("hellosales", "HelloSales backend service information")

# Request metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Pipeline metrics
PIPELINE_RUNS_TOTAL = Counter(
    "pipeline_runs_total",
    "Total pipeline runs",
    ["pipeline_name", "status"],
)

PIPELINE_DURATION_SECONDS = Histogram(
    "pipeline_duration_seconds",
    "Pipeline execution latency in seconds",
    ["pipeline_name"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

PIPELINE_ACTIVE = Gauge(
    "pipeline_runs_active",
    "Number of currently active pipeline runs",
    ["pipeline_name"],
)

# Stage metrics
STAGE_EXECUTIONS_TOTAL = Counter(
    "stage_executions_total",
    "Total stage executions",
    ["pipeline_name", "stage_name", "status"],
)

STAGE_DURATION_SECONDS = Histogram(
    "stage_duration_seconds",
    "Stage execution latency in seconds",
    ["pipeline_name", "stage_name"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# LLM provider metrics
LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Total LLM provider requests",
    ["provider", "model", "status"],
)

LLM_REQUEST_DURATION_SECONDS = Histogram(
    "llm_request_duration_seconds",
    "LLM request latency in seconds",
    ["provider", "model"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

LLM_TOKENS_TOTAL = Counter(
    "llm_tokens_total",
    "Total LLM tokens used",
    ["provider", "model", "direction"],  # direction: input/output
)

LLM_COST_CENTS_TOTAL = Counter(
    "llm_cost_cents_total",
    "Total LLM cost in cents",
    ["provider", "model"],
)

# Session metrics
SESSIONS_ACTIVE = Gauge(
    "sessions_active",
    "Number of active sessions",
)

SESSIONS_TOTAL = Counter(
    "sessions_total",
    "Total sessions created",
    ["org_id"],
)

INTERACTIONS_TOTAL = Counter(
    "interactions_total",
    "Total interactions",
    ["session_id", "role"],
)

# Guard metrics
GUARD_BLOCKS_TOTAL = Counter(
    "guard_blocks_total",
    "Total guard block events",
    ["guard_type", "category"],  # guard_type: input/output
)

# Circuit breaker metrics
CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    ["name"],
)

CIRCUIT_BREAKER_FAILURES_TOTAL = Counter(
    "circuit_breaker_failures_total",
    "Total circuit breaker failures",
    ["name"],
)

# Database metrics
DB_CONNECTIONS_ACTIVE = Gauge(
    "db_connections_active",
    "Number of active database connections",
)

DB_QUERIES_TOTAL = Counter(
    "db_queries_total",
    "Total database queries",
    ["table", "operation"],  # operation: select, insert, update, delete
)

DB_QUERY_DURATION_SECONDS = Histogram(
    "db_query_duration_seconds",
    "Database query latency in seconds",
    ["table", "operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)


def set_service_info(version: str, environment: str) -> None:
    """Set service information.

    Args:
        version: Service version
        environment: Deployment environment
    """
    SERVICE_INFO.info({
        "version": version,
        "environment": environment,
    })


def record_http_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    """Record an HTTP request.

    Args:
        method: HTTP method
        endpoint: Request endpoint
        status_code: Response status code
        duration_seconds: Request duration in seconds
    """
    HTTP_REQUESTS_TOTAL.labels(
        method=method,
        endpoint=endpoint,
        status_code=str(status_code),
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=method,
        endpoint=endpoint,
    ).observe(duration_seconds)


def record_pipeline_run(
    pipeline_name: str,
    status: str,
    duration_seconds: float,
) -> None:
    """Record a pipeline run.

    Args:
        pipeline_name: Pipeline name
        status: Run status (success, failure, cancelled)
        duration_seconds: Run duration in seconds
    """
    PIPELINE_RUNS_TOTAL.labels(
        pipeline_name=pipeline_name,
        status=status,
    ).inc()
    PIPELINE_DURATION_SECONDS.labels(
        pipeline_name=pipeline_name,
    ).observe(duration_seconds)


def record_stage_execution(
    pipeline_name: str,
    stage_name: str,
    status: str,
    duration_seconds: float,
) -> None:
    """Record a stage execution.

    Args:
        pipeline_name: Pipeline name
        stage_name: Stage name
        status: Execution status
        duration_seconds: Execution duration in seconds
    """
    STAGE_EXECUTIONS_TOTAL.labels(
        pipeline_name=pipeline_name,
        stage_name=stage_name,
        status=status,
    ).inc()
    STAGE_DURATION_SECONDS.labels(
        pipeline_name=pipeline_name,
        stage_name=stage_name,
    ).observe(duration_seconds)


def record_llm_request(
    provider: str,
    model: str,
    status: str,
    duration_seconds: float,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_cents: int = 0,
) -> None:
    """Record an LLM request.

    Args:
        provider: LLM provider name
        model: Model name
        status: Request status
        duration_seconds: Request duration in seconds
        tokens_in: Input tokens
        tokens_out: Output tokens
        cost_cents: Cost in cents
    """
    LLM_REQUESTS_TOTAL.labels(
        provider=provider,
        model=model,
        status=status,
    ).inc()
    LLM_REQUEST_DURATION_SECONDS.labels(
        provider=provider,
        model=model,
    ).observe(duration_seconds)

    if tokens_in > 0:
        LLM_TOKENS_TOTAL.labels(
            provider=provider,
            model=model,
            direction="input",
        ).inc(tokens_in)

    if tokens_out > 0:
        LLM_TOKENS_TOTAL.labels(
            provider=provider,
            model=model,
            direction="output",
        ).inc(tokens_out)

    if cost_cents > 0:
        LLM_COST_CENTS_TOTAL.labels(
            provider=provider,
            model=model,
        ).inc(cost_cents)


def record_guard_block(guard_type: str, category: str) -> None:
    """Record a guard block event.

    Args:
        guard_type: Guard type (input/output)
        category: Block category
    """
    GUARD_BLOCKS_TOTAL.labels(
        guard_type=guard_type,
        category=category,
    ).inc()
