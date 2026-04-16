# Codebase Map

## Purpose
This document maps the backend package structure to responsibilities.

Root package:
- `backend/src/hello_sales_backend/`

## Package Overview

### `app.py`
Owns:
- FastAPI application factory
- middleware registration
- error handler registration
- top-level router mounting
- lifespan integration with the composition root

### `application/`
Owns application-level policy that should not live in platform runtime packages.

#### `application/agents/`
Owns:
- agent registry assembly
- concrete agent definitions
- per-agent policy and selection behavior

#### `application/tools/`
Owns:
- reusable application-level tools used by agents

### `entrypoints/`
Owns transport adapters.

#### `entrypoints/http/`
Owns:
- API router
- route handlers
- route dependencies
- transport schemas
- transport-level error handling

Current route groups:
- `health`
- `agent_runs`
- `jobs`
- `system`

### `modules/`
Owns public application capability surfaces.

#### `modules/system/`
Owns:
- system status and diagnostics capability
- views and ports for operator-facing runtime inspection

#### `modules/jobs/`
Owns:
- operational jobs capability
- diagnostic workflow orchestration through application-level services

#### `modules/agent_runs/`
Owns:
- public operational surface for generic agent runs
- run lifecycle actions
- event replay / inspection
- approval and cancellation surfaces

### `platform/`
Owns runtime infrastructure.

#### `platform/agents/`
Owns:
- generic agent runtime mechanics
- runtime config and models
- persistence contracts
- tool execution context/contracts

#### `platform/composition/`
Owns:
- top-level container assembly
- provider assembly
- startup hooks
- composition-time overrides for tests and environment-specific wiring

#### `platform/config/`
Owns:
- settings parsing and environment-driven runtime config

#### `platform/db/`
Owns:
- engine and session construction
- unit-of-work factory
- SQLAlchemy-backed stores and repositories

#### `platform/observability/`
Owns:
- structured logging helpers
- request-context middleware
- health service
- operational event and alert runtime
- observability data models

#### `platform/providers/`
Owns:
- concrete provider integrations and provider contracts
- current LLM provider seam

#### `platform/tasks/`
Owns:
- task metadata and task state models
- background task runner and task event persistence seam

#### `platform/workflows/`
Owns:
- workflow runtime wrapper
- workflow executor facade
- workflow registry support

### `shared/`
Owns cross-cutting shared code.

Current shared concerns include:
- errors
- ids
- generic shared helpers and types

### `smoke/`
Owns the centralized smoke harness.

Owns:
- smoke contracts
- registry
- runner
- shared support helpers
- smoke suites

## High-Signal Files

### Composition And App Assembly
- `app.py`
- `platform/composition/app_container.py`
- `platform/composition/startup.py`
- `platform/composition/providers.py`
- `platform/composition/overrides.py`

### Operational Runtime
- `platform/observability/runtime.py`
- `platform/tasks/runner.py`
- `platform/workflows/runtime.py`
- `platform/workflows/executor.py`

### Public Application Facades
- `modules/system/use_cases/system_service.py`
- `modules/jobs/use_cases/jobs_service.py`
- `modules/agent_runs/use_cases/agent_run_service.py`

### Generic Agent Runtime
- `platform/agents/runtime.py`
- `application/agents/bootstrap.py`

### Transport Entry Surface
- `entrypoints/http/router.py`
- `entrypoints/http/routes/`

## Test Layout

### `tests/unit/`
Focused unit tests for runtime components, provider seams, task runner, smoke runner, and registry behavior.

### `tests/integration/`
Focused integration tests for app factory, overrides, event streaming, and error contract behavior.

### `tests/smoke/`
HTTP and runtime smoke validation for health, jobs, system, agent runs, and provider-backed smoke behavior.

### `tests/postgres/`
Optional Postgres-backed verification for readiness and SQLAlchemy-backed persistence.
