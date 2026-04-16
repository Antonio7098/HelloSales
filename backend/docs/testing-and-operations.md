# Testing And Operations

## Purpose
This document explains how the backend is verified and how to operate the scaffold during development.

## Test Layout

The backend test suite is split into four layers.

### `tests/unit/`
Owns fast unit verification for:
- generic agent runtime behavior
- provider adapters and provider registry
- task runner behavior
- smoke runner behavior
- module scaffold generator behavior

### `tests/integration/`
Owns integration verification for:
- app factory and app assembly
- composition overrides
- agent event stream behavior
- error contract behavior

### `tests/smoke/`
Owns high-signal smoke verification for:
- health surface
- agent-runs surface
- jobs diagnostic flow
- system diagnostics and system status
- provider-backed smoke behavior

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
- OpenAI-compatible provider seam
- request context middleware
- request, provider, workflow, and task failure logging
- background task runner
- health endpoints
- diagnostics endpoint
- a system module
- an operational jobs module with a diagnostic workflow
- an agent-runs module exposing the generic agent runtime

## Recommended Reading With This Doc

For runtime structure:
- `runtime-overview.md`

For package ownership:
- `codebase-map.md`

For public surfaces and extension points:
- `api-and-runtime-surfaces.md`
