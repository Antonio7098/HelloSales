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

#### `application/workers/`
Owns:
- worker registry assembly
- concrete worker definitions
- per-worker schema and prompt policy

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
- `sessions`
- `worker_runs`
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

#### `modules/sessions/`
Owns:
- public session-first conversational surface
- durable session ownership and chronology
- session summary and attached execution entrypoints

#### `modules/agent_runs/`
Owns:
- attached execution surface for generic agent runs
- run lifecycle actions
- event replay / inspection
- approval and cancellation surfaces

#### `modules/worker_runs/`
Owns:
- public operational surface for generic worker runs
- worker lifecycle actions
- worker event inspection
- cancellation surface

### `platform/`
Owns runtime infrastructure.

#### `platform/agents/`
Owns:
- generic agent runtime mechanics
- context profiles, context source contracts, source provenance, and default session context source
- runtime config and models
- persistence contracts
- tool execution context/contracts

#### `platform/sessions/`
Owns:
- neutral session models
- session persistence seams
- attached execution mirroring into session chronology
- session summary prompt and lifecycle helpers

#### `platform/composition/`
Owns:
- top-level container assembly
- provider assembly
- startup hooks
- composition-time overrides for tests and environment-specific wiring

#### `platform/config/`
Owns:
- settings parsing and environment-driven runtime config

#### `platform/llm/`
Owns:
- neutral LLM contracts
- text and JSON generation response models
- JSON schema hints
- OpenAI-compatible provider adapters

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

#### `platform/tasks/`
Owns:
- task metadata and task state models
- background task runner and task event persistence seam

#### `platform/workers/`
Owns:
- generic worker runtime mechanics
- worker run and event models
- worker persistence seams
- worker diagnostics summary surface

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
- `modules/sessions/use_cases/session_service.py`
- `modules/agent_runs/use_cases/agent_run_service.py`
- `modules/worker_runs/use_cases/worker_run_service.py`

### Generic Agent Runtime
- `platform/agents/runtime.py`
- `platform/agents/context.py`
- `application/agents/bootstrap.py`

### Generic Worker Runtime
- `platform/workers/runtime.py`
- `application/workers/bootstrap.py`

### Transport Entry Surface
- `entrypoints/http/router.py`
- `entrypoints/http/routes/`

## Test Layout

### `tests/unit/`
Focused unit tests for runtime components, provider seams, task runner, smoke runner, and registry behavior.

### `tests/integration/`
Focused integration tests for app factory, overrides, event streaming, worker runtime wiring, and error contract behavior.

### `tests/smoke/`
HTTP and runtime smoke validation for health, jobs, system, agent runs, worker runs, and provider-backed smoke behavior.

### `tests/postgres/`
Optional Postgres-backed verification for readiness and SQLAlchemy-backed persistence.
