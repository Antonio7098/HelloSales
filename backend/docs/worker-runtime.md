# Worker Runtime

## Purpose
This document explains the implemented worker runtime.

It focuses on:
- the split between the neutral LLM substrate, worker runtime, and operational exposure
- worker lifecycle, retries, timeout handling, and cancellation
- local structured-output validation
- how worker telemetry appears in metrics, traces, diagnostics, and events

## Architectural Split

The worker system is deliberately split into three layers.

### 1. Neutral LLM Substrate
Location:
- `src/hello_sales_backend/platform/llm/`

Owns:
- normalized text and JSON generation contracts
- provider-facing response models
- JSON schema hint helpers
- OpenAI-compatible provider adapters

This layer should not own:
- worker retry policy
- worker validation policy
- agent tool or approval behavior

### 2. Generic Worker Runtime
Location:
- `src/hello_sales_backend/platform/workers/`

Owns:
- worker run state models
- worker event models
- persistence seams
- execution lifecycle
- retry and timeout handling
- local output validation
- optional final-attempt backup-provider seam

This layer should not own:
- concrete worker prompts
- product-specific worker semantics
- transport behavior

### 3. Application-Owned Worker Policy And Exposure
Locations:
- `src/hello_sales_backend/application/workers/`
- `src/hello_sales_backend/modules/worker_runs/`

Owns:
- concrete worker definitions
- input/output schema selection
- prompt-building policy
- operational use cases for start, inspect, list events, and cancel

## Main Runtime Components

### `WorkerRuntime`
Location:
- `platform/workers/runtime.py`

Responsibilities:
- load worker run state
- validate the stored input payload against the worker input model
- request provider-native JSON output through the neutral LLM substrate
- validate JSON locally against the worker output model
- retry on invalid JSON, validation failure, timeout, or retryable provider failure
- switch to the configured backup provider on the final allowed attempt when available
- mark completion, failure, or cancellation explicitly
- append ordered worker events
- emit observability events and worker telemetry signals

### `WorkerRunService`
Location:
- `modules/worker_runs/use_cases/worker_run_service.py`

Responsibilities:
- validate worker selection and input payload shape
- create the persisted worker run
- schedule execution through the background task runner
- optionally route execution through the app-owned Stageflow boundary
- expose run detail, events, and cancellation through a stable module facade

### Worker Registry
Location:
- `application/workers/bootstrap.py`
- `application/workers/registry.py`

The current application worker registry includes:
- `structured-brief`

This sample worker stays intentionally generic. It exists to exercise the runtime boundary, not to commit the backend to a product-specific workflow.

## Lifecycle Model

Worker runs currently move through:
- `pending`
- `running`
- `retrying`
- `completed`
- `failed`
- `cancelled`

Important details:
- `attempt_count` is persisted on the run
- `max_attempts` is fixed when the run is created
- each retry is recorded as an ordered worker event
- terminal failure always preserves a structured error code, category, message, and details payload

## Validation And Retry Model

Validation is local and authoritative.

The runtime currently:
- asks the provider for JSON output
- parses the returned text locally
- validates the parsed payload against the worker output model
- optionally applies worker-specific semantic validation

Retry behavior is layered:
- provider transport errors stay provider-classified
- worker runtime retries invalid JSON and validation failures
- the final attempt may switch to the optional backup provider seam

This keeps provider strictness as guidance rather than correctness.

## Stageflow Compatibility

Workers can run in two execution modes:
- `direct`
- `stageflow`

`stageflow` mode stays behind the app-owned workflow executor.
The worker runtime still owns its own run state, retry behavior, and terminal status even when Stageflow is the orchestration boundary.

## Observability Model

Worker runtime visibility extends the platform-owned observability runtime introduced earlier in the scaffold.

Current worker monitoring surfaces include:
- ordered worker events on the run itself
- operational events emitted through `ObservabilityRuntime`
- Prometheus worker metric families when metrics are enabled
- worker tracing spans when tracing is enabled
- worker summaries in `GET /api/system/diagnostics`

Current worker metric families include:
- `hello_sales_worker_runs_started_total`
- `hello_sales_worker_runs_completed_total`
- `hello_sales_worker_runs_active`
- `hello_sales_worker_run_duration_seconds`

Worker tracing spans preserve:
- `request_id`
- `trace_id`
- worker run id
- worker name
- execution mode

## HTTP Surface

Operational worker endpoints live under:
- `/api/worker-runs`

Current actions:
- `POST /api/worker-runs`
- `GET /api/worker-runs/{run_id}`
- `GET /api/worker-runs/{run_id}/events`
- `POST /api/worker-runs/{run_id}/cancel`

These remain operational-only surfaces.
