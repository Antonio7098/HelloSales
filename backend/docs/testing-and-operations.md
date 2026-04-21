# Testing And Operations

## Purpose
This document explains how the backend is verified and how to operate the scaffold during development.

## Test Layout

The backend test suite is split into four layers.

### `tests/unit/`
Owns fast unit verification for:
- generic agent runtime behavior
- worker runtime behavior
- provider adapters and provider registry
- analytics-query manifest, validator, risk, and redaction behavior
- task runner behavior
- smoke runner behavior
- module scaffold generator behavior

### `tests/integration/`
Owns integration verification for:
- app factory and app assembly
- composition overrides
- agent event stream behavior
- analytics-query wiring and failure translation
- error contract behavior
- worker-runs operational behavior and metrics visibility

### `tests/smoke/`
Owns high-signal smoke verification for:
- health surface
- agent-runs surface
- worker-runs surface
- jobs diagnostic flow
- system diagnostics and system status
- provider-backed smoke behavior, including the governed analytics-query path in the generic-agent provider suite

### `tests/postgres/`
Owns optional Postgres-backed verification for:
- readiness behavior against Postgres
- SQLAlchemy-backed agent store behavior

## Smoke Harness

The canonical smoke harness lives in:
- `src/hello_sales_backend/smoke/`
- `scripts/smoke.py`

The CLI entrypoint:
- lists registered smoke suites
- runs one named suite
- prints structured JSON results
- returns non-zero exit codes on failure or timeout

Current provider-backed suites include:
- `generic-agent-provider`
- `generic-agent-provider-baseline`
- `observer-agent-provider`
- `generic-agent-provider-append-turn`
- `generic-agent-provider-approval-boundary`
- `generic-agent-provider-event-stream`
- `generic-agent-provider` scenario `analytics_query_completion`
- `worker-provider-baseline`

## Development Operations

### Local Database
The backend is Postgres-first for development and production.

Common commands from `backend/`:
- `make dev-db-up`
- `make dev-db-down`
- `make dev-db-logs`
- `make verify-db`

### Migrations
Common commands:
- `make migrate`
- `make revision message="add task table"`

### Tests
Common commands:
- `make test`
- `HELLO_SALES_RUN_POSTGRES_TESTS=1 python3 -m pytest tests/postgres -q`

### Smoke Commands
Examples:
- `python3 scripts/smoke.py --list`
- `make smoke`
- `make smoke-provider-baseline`
- `make smoke-provider-observer`
- `make smoke-provider-append`
- `make smoke-provider-approval`
- `make smoke-provider-events`
- `make smoke-provider-worker`

The governed analytics-query smoke path uses the existing `generic-agent-provider` suite rather than a separate SQL-specific harness.
In test mode it seeds a bounded SQLite fixture before app startup so the conversational tool path can be exercised deterministically.

## Environment Model

The backend reads runtime settings from `HELLO_SALES_*` environment variables.
The generic-agent provider path uses provider-specific env such as:
- `GENERIC_AGENT_PROVIDER`
- `GENERIC_AGENT_MODEL`
- provider API key variables such as `GROQ_API_KEY`
- optional timeout/base-url overrides

## Current Operational Scope

The scaffold currently provides:
- FastAPI app factory
- async SQLAlchemy runtime
- composition root
- Stageflow runtime boundary
- neutral LLM substrate with an OpenAI-compatible adapter
- request context middleware
- request, provider, workflow, and task failure logging
- background task runner
- health endpoints
- diagnostics endpoint
- a governed analytics-query module and semantic YAML catalog path
- a system module
- an operational jobs module with a diagnostic workflow
- an agent-runs module exposing the generic agent runtime
- a worker-runs module exposing the worker runtime

## Recommended Reading With This Doc

For runtime structure:
- `runtime-overview.md`

For package ownership:
- `codebase-map.md`

For public surfaces and extension points:
- `api-and-runtime-surfaces.md`
