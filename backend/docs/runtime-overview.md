# Backend Runtime Overview

## Purpose
This document explains the implemented runtime model of the HelloSales backend.

It describes:
- how the app starts
- how the composition root is assembled
- how requests, background jobs, sessions, attached agent execution, and worker runs flow through the system
- which runtime services are foundational

## Top-Level Shape

The backend is a FastAPI application with a composition-root-driven runtime graph.

The main runtime areas are:
- `app.py` - FastAPI app factory and lifespan wiring
- `platform/composition/` - application assembly
- `entrypoints/http/` - transport adapters
- `modules/` - application capability surfaces
- `platform/` - runtime infrastructure
- `application/` - agent policy and reusable application-level tools
- `smoke/` - centralized smoke harness

## Startup Flow

The primary startup path is:

```text
create_app()
-> build_app_container()
-> FastAPI lifespan
-> bootstrap_container()
-> settings validation
-> optional database reachability check
-> startup log + operational event emission
```

### Entry Point
- `src/hello_sales_backend/app.py`

`create_app()`:
- resolves settings
- configures logging
- builds the app container
- registers middleware and error handlers
- mounts the top-level API router
- optionally mounts the operational metrics endpoint
- runs startup and shutdown through the FastAPI lifespan

### Composition Root
- `src/hello_sales_backend/platform/composition/app_container.py`
- `src/hello_sales_backend/platform/composition/startup.py`
- `src/hello_sales_backend/platform/composition/providers.py`
- `src/hello_sales_backend/platform/composition/overrides.py`

`build_app_container()` assembles:
- database runtime
- provider registry
- auth module and auth middleware
- worker store
- observability runtime
- background task runner
- workflow runtime and executor
- health service
- analytics-query, system, jobs, sessions, agent-runs, and worker-runs modules
- agent registry and generic agent runtime
- worker registry and worker runtime

## Runtime Services

### Database Runtime
The container builds:
- SQLAlchemy engine
- async session factory
- unit-of-work factory
- task run store
- agent store
- session store

This is exposed through `DatabaseRuntime` in `platform/composition/app_container.py`.

### Provider Registry
The provider registry owns external provider adapters, including auth, LLM, and web search.

- `platform/composition/providers.py`
- `platform/auth/`
- `platform/llm/`

Behavior:
- uses WorkOS for auth when configured
- falls back to a no-op auth provider for local/test-only assembly
- uses an OpenAI-compatible provider when configured
- falls back to a noop provider when no real provider is configured
- exposes provider diagnostics and close hooks
- supports both text generation and provider-native JSON generation through one neutral substrate

### Auth Runtime
The auth runtime lives in:
- `platform/auth/`
- `modules/auth/`
- `entrypoints/http/routes/auth.py`

Execution shape:

```text
HTTP request
-> AuthenticationMiddleware
-> AuthService.authenticate_request()
-> AuthProviderPort.authenticate()
-> request.state.auth_context
-> route permission dependencies
```

The backend authorizes through explicit permission slugs, not hard-coded binary roles. WorkOS roles and permissions are mapped into the provider-neutral `AuthContext`, then route dependencies and agent tool execution enforce backend-owned permissions.

Session-backed agent runs persist `org_id` and permission snapshots so approvals, background execution, and tool calls continue with the authorization context from the authenticated request.

### Observability Runtime
The observability runtime owns:
- operational event emission
- in-memory event retention for scaffold-stage visibility
- code/severity-driven alert derivation
- Prometheus metrics collection and exposition
- OpenTelemetry tracing hooks for HTTP and background task boundaries
- collector-oriented tracing export through `console`, `none`, or OTLP HTTP exporters

- `platform/observability/runtime.py`

Supporting files now include:
- `platform/observability/metrics.py`
- `platform/observability/telemetry.py`
- `platform/observability/middleware.py`
- `platform/observability/health.py`

The first instrumentation layer covers:
- HTTP request counts, latency, outcomes, and active requests
- liveness/readiness status
- background task start, terminal state, failure-like counts, and duration
- worker run start, terminal state, active-count, and duration

The metrics surface is mounted directly on the FastAPI app at a configurable path, defaulting to `/metrics` when enabled. It remains outside the `/api` router because it is an operator surface rather than a product API capability.

Tracing is additive rather than replacement behavior:
- existing `request_id` and `trace_id` metadata remain intact for logs, events, and errors
- telemetry adds spans for HTTP, background task, and worker execution where enabled
- structured logs and operational events remain the authoritative failure record

Sprint 03 extends this runtime toward a self-hosted stack:
- the backend can now export spans to an OTLP HTTP endpoint suitable for an OpenTelemetry Collector
- repo-owned observability stack config lives under `backend/ops/observability/`
- the intended deployment path is app -> OpenTelemetry Collector -> Tempo/Loki/Prometheus/Grafana

### Background Task Runner
The task runner owns:
- task scheduling
- task snapshot state
- task failure capture
- operational event emission for failed tasks
- cancellation on shutdown

- `platform/tasks/runner.py`

### Workflow Runtime
The workflow runtime is an app-owned wrapper around Stageflow availability.

- `platform/workflows/runtime.py`
- `platform/workflows/executor.py`

The runtime wrapper:
- loads Stageflow dynamically
- enforces required-vs-optional installation semantics
- exposes a stable executor surface to modules

## Application Capability Modules

The backend currently exposes seven modules:

### `modules/auth`
Purpose:
- hosted-auth login URL creation
- callback code exchange and session cookie establishment
- current-session projection
- logout redirect and cookie clearing

### `modules/analytics_query`
Purpose:
- governed analytics-query capability for the conversational runtime
- semantic catalog loading from YAML manifests
- `sqlglot`-backed read-only validation against approved relations and columns
- bounded execution, result truncation, and semantics-aware redaction
- machine-usable query observability events such as `analytics_query.succeeded` and `analytics_query.failed`

### `modules/sessions`
Purpose:
- session-first conversational API
- durable conversation chronology
- session summary state and materialized summaries
- approval and cancellation entrypoints for attached execution

### `modules/system`
Purpose:
- system status
- diagnostics
- operator-facing runtime introspection

The system service reports:
- app/runtime metadata
- provider diagnostics
- task diagnostics
- agent diagnostics
- recent operational events
- active alerts

### `modules/jobs`
Purpose:
- lightweight operational jobs
- diagnostic workflow execution
- task inspection

The jobs service starts a diagnostic LLM workflow through the task runner and workflow executor.

### `modules/agent_runs`
Purpose:
- attached execution facade over the generic agent runtime
- run creation, append-turn, approval, event replay, cancellation for session-backed execution

The agent-runs module remains an internal-facing execution module while `/sessions` is the public conversation root.

### `modules/worker_runs`
Purpose:
- operational surface for structured worker runs
- run creation, inspection, event listing, and cancellation

The worker-runs module is the public application facade over the worker runtime.

## Session And Agent Execution Model

The generic agent runtime lives in:
- `platform/agents/runtime.py`

Execution shape:

```text
SessionService
-> receive AuthContext from HTTP dependency
-> create session + first user message
-> AgentRunService.start_run(session_id=..., auth_context=...)
-> schedule background task
-> GenericAgentRuntime.process_turn()
-> Stageflow-backed pipeline
   -> prepare_turn
   -> execute_tools
   -> generate_response
-> mirror chronology into session items
-> optionally schedule session summary generation
-> persist run/turn/tool/event state
-> emit operational signal on failure
```

The combined session/agent runtime currently owns:
- session lifecycle state
- session item chronology
- agent run and turn lifecycle state
- tool-call lifecycle state
- approval pause handling
- governed analytics-query tool execution through the normal persisted tool-call lifecycle
- actor, org, and permission propagation through long-lived execution
- summary task lifecycle and materialized summary state
- completion / failure / cancellation transitions

## Worker Execution Model

The worker runtime lives in:
- `platform/workers/runtime.py`

Execution shape:

```text
WorkerRunService
-> create worker run
-> schedule background task
-> optional WorkflowExecutor.run_worker_run_workflow()
-> WorkerRuntime.process_run()
-> provider JSON generation through platform/llm
-> local validation + bounded retries
-> persist run + event state
-> emit worker telemetry and operational events
```

The runtime currently owns:
- worker lifecycle state
- local structured-output validation
- retry and timeout handling
- optional backup-provider selection
- event append-only history
- completion / failure / cancellation transitions

## HTTP Surface Model

The top-level router lives in:
- `entrypoints/http/router.py`

Mounted route groups:
- `/health`
- `/sessions`
- `/worker-runs`
- `/jobs`
- `/system`

Routes are intended to remain thin adapters over module services.

## Testing And Verification Model

Tests are split into:
- `tests/unit/`
- `tests/integration/`
- `tests/smoke/`
- `tests/postgres/`

The smoke harness is implemented under:
- `src/hello_sales_backend/smoke/`
- `scripts/smoke.py`

## Current Character Of The Backend

This backend is currently a scaffold-stage operational backend.
It is strongest in:
- runtime plumbing
- agent run lifecycle support
- diagnostics and observability surfaces
- smoke-driven provider verification
- explicit composition and replaceable seams

It is intentionally not yet a product-domain backend.
