# Diagnostics And Events

## Purpose
This document explains the backend's current diagnostics, health, event, and alert surfaces.

It focuses on:
- health and readiness behavior
- operational events
- alerts
- diagnostics aggregation
- what is inspectable today versus what is only scaffold-stage in-memory state

## Main Diagnostics Surfaces

The backend currently exposes diagnostics through three related mechanisms:
- health endpoints
- system diagnostics endpoints
- operational event and alert runtime state
- metrics and telemetry runtime state

## Health Model

Health behavior lives in:
- `src/hello_sales_backend/platform/observability/health.py`

### Liveness
Liveness is intentionally shallow.

It currently reports:
- process is live
- database status as `unknown`
- workflows as `ok`

The point of liveness is only to say the process is up, not that dependencies are fully healthy.

### Readiness
Readiness is dependency-aware.

It currently checks:
- database configuration and reachability when using non-SQLite DBs
- workflow runtime availability relative to whether workflows are required

Possible readiness outcomes include:
- `ready`
- `degraded`
- dependency-driven failure via structured app error

Readiness and liveness now also update machine-usable metrics so the same dependency truth is available through `/metrics`.

### Database Readiness Semantics
Behavior:
- SQLite paths are treated differently from external DB paths
- non-SQLite DBs are actively pinged during readiness
- failure becomes a structured dependency error

### Workflow Readiness Semantics
Behavior:
- if workflows are required and unavailable, readiness fails
- if workflows are optional and unavailable, readiness degrades rather than hard failing

## Operational Event Model

The core event model lives in:
- `platform/observability/events.py`

An `OperationalEvent` currently includes:
- `event_type`
- `severity`
- `component`
- `operation`
- `correlation_id`
- `trace_id`
- `code`
- `payload`

The model is intentionally structured so the event can support diagnostics, alerting, and review.

## Operational Event Runtime

The current runtime implementation lives in:
- `platform/observability/runtime.py`

The scaffold-stage runtime uses:
- `InMemoryOperationalStore`
- `AlertPolicy`
- `ObservabilityRuntime`

### In-Memory Store
The in-memory store currently keeps:
- recent operational events
- active alerts

This is good for scaffold-stage inspection, but it is not a durable production event store.

### Alert Policy
The current alert policy is intentionally small.

Behavior:
- events with severity `error` or `critical` generate alerts
- lower-severity events do not
- alert records preserve key contextual metadata such as component, operation, code, and correlation identifiers

## Where Events Come From Today

Important current producers include:
- startup completion and startup failure in `platform/composition/startup.py`
- background task failure in `platform/tasks/runner.py`
- agent run failure in `platform/agents/runtime.py`

This is important because the diagnostics surface is not just passive storage; it reflects events emitted by runtime services.

## System Diagnostics Aggregation

The main aggregated diagnostics surface lives in:
- `modules/system/use_cases/system_service.py`

`SystemService.get_diagnostics()` currently aggregates:
- app metadata
- environment
- database scheme
- workflow engine and installation status
- provider diagnostics
- task diagnostics
- agent diagnostics
- observability runtime configuration and enablement state
- recent operational events
- active alerts

This makes the `system` module the main operator-facing diagnostics facade.

## Metrics Surface

The canonical operational metrics surface is:
- `/metrics` when `HELLO_SALES_OBSERVABILITY_METRICS_ENDPOINT_ENABLED=true`

Important characteristics:
- it is an operational surface, not a product API capability
- it is mounted directly on the app rather than under `/api`
- it exposes Prometheus text format
- it is intentionally narrow and machine-oriented

Current metric families cover:
- HTTP requests
- health and readiness truth
- background task lifecycle

High-cardinality values such as request ids, trace ids, task ids, and raw error messages are intentionally excluded from metric labels.

## Telemetry Runtime State

System diagnostics now expose a concise observability summary.

That summary includes:
- whether metrics are enabled
- whether the metrics endpoint is enabled and where it is mounted
- whether tracing is enabled
- which tracing exporter is configured
- which metric families and tracing boundaries are active

This keeps diagnostics operator-useful without turning the diagnostics endpoint into a monitoring dashboard.

## Task Diagnostics

Task diagnostics come from:
- `platform/tasks/runner.py`

The task runner exposes:
- active count
- failure count
- total snapshot count
- recent task snapshots

Task snapshots preserve:
- task identity
- purpose
- request/trace/actor metadata
- lifecycle timestamps
- structured failure summary when applicable

## Agent Diagnostics

Agent diagnostics currently come from the agent store summary surface.

The diagnostics summary includes:
- active run count
- awaiting-approval count
- total run count
- recent runs

This complements the richer per-run inspection surfaces in the `agent_runs` module.

## Inspectability Model

Today, the backend is intentionally optimized for inspectability.

You can inspect runtime behavior through:
- health/readiness responses
- system diagnostics responses
- agent-run detail and event views
- task snapshots
- recent operational events
- active alerts

## Current Limitations

Important current limitations:
- operational events and alerts are in-memory, not durable
- diagnostics are scaffold-stage and optimized for visibility, not yet long-term analytics
- alerting policy is intentionally minimal
- some signals now exist across logs, operational events, metrics, and traces by design rather than through a single sink
- deeper provider, workflow, and agent telemetry remains intentionally shallow after the foundation sprint

## Where To Read In Code

High-signal files:
- `platform/observability/health.py`
- `platform/observability/events.py`
- `platform/observability/runtime.py`
- `platform/tasks/runner.py`
- `platform/agents/runtime.py`
- `platform/composition/startup.py`
- `modules/system/use_cases/system_service.py`
