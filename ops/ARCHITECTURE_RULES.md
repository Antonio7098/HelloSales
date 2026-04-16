# Architecture Rules

## Purpose
This document is the ongoing guide for how backend code must be added to this project.

It governs:
- filesystem structure
- import direction
- composition and dependency injection
- service boundaries
- orchestration boundaries
- testing seams
- operational plumbing

Use this document as the default source of truth when adding new backend code.
Use [APPLICATION_BLUEPRINT.md](/home/antonioborgerees/coding/HelloSales/ops/APPLICATION_BLUEPRINT.md) for the concrete foundation layout and startup shape.
Use [GENERIC_AGENT_PLAN.md](/home/antonioborgerees/coding/HelloSales/ops/GENERIC_AGENT_PLAN.md) when adding generic agent runtime capabilities.
Use [OPERATIONAL_CONTRACT.md](/home/antonioborgerees/coding/HelloSales/ops/OPERATIONAL_CONTRACT.md) for failure handling, observability, and fail-fast operational rules.

## Core Principles

1. One module = one bounded context.
2. Dependency direction points inward toward business logic.
3. High-level policy depends on abstractions, not concrete infra.
4. Routes, jobs, and sockets are translation layers only.
5. Infrastructure is replaceable.
6. Test seams are a first-class architectural concern.
7. The app must remain operationally observable under failure, not only functionally correct on the happy path.

## SOLID In Practice

### Single Responsibility Principle
Each class, function, and module must have one reason to change.

Apply it as follows:
- `domain` models business behavior
- `use_cases` coordinate application actions
- `workflows` orchestrate multi-step processes
- `infra` translates to external systems
- `entrypoints` translate external input into application calls

Reject changes where one class handles business rules, persistence, provider calls, and HTTP concerns together.

### Open/Closed Principle
Prefer adding a new port implementation, workflow, or module bootstrap over editing unrelated existing code paths.

Do not introduce speculative abstractions. Add extension points only where variation is real or likely.

### Liskov Substitution Principle
Every implementation behind a port must preserve its contract.

Examples:
- repository implementations must agree on missing-record behavior
- provider adapters must agree on timeout, error, and response semantics
- fake test doubles must match production contracts

If callers need implementation-specific branching, the abstraction is wrong.

### Interface Segregation Principle
Ports must be narrow and use-case-driven.

Do:
- split read and write ports when consumers differ
- expose small route-facing service interfaces
- keep module public APIs minimal

Do not create broad repository or provider interfaces with unrelated capabilities.

### Dependency Inversion Principle
Use cases and workflows must depend on ports, not concrete repositories, sessions, SDK clients, or vendor adapters.

This is the main architectural rule behind this document.

## Non-Negotiable Technical Rules

### 1. Async Policy
This project uses an async application surface. New persistence and external I/O code must be async-compatible.

Required:
- use async-first interfaces at the application boundary
- use async SQLAlchemy if request handlers and workflows are async
- use async HTTP clients for network calls

Not allowed:
- sync database access inside async request handlers
- sync external API calls inside async workflows
- mixing async edges with ad hoc blocking internals

If a sync dependency is unavoidable, isolate it behind an explicit adapter boundary and run it off the event loop.

### 2. Composition Root Policy
There must be one application composition root, but it must not become a god-object.

Required:
- top-level app assembly lives in `platform/composition/`
- each module owns a `bootstrap.py` or equivalent registrar
- the top-level container composes modules and shared platform services

Not allowed:
- one file that knows every repository, guard, provider, broker, and workflow detail in the system
- routes reaching through the container into private service internals

### 3. Ports First
Repository, provider, broker, and gateway contracts live in the application layer.

Required:
- define ports in `use_cases/ports.py`
- implement ports in `infra/`
- inject implementations during composition

Not allowed:
- `use_cases` importing concrete infra classes
- module root exporting concrete infra implementations as public API
- platform DB models leaking into use cases

### 4. Route and Socket Boundary Policy
HTTP routes, webhooks, CLI handlers, and websocket handlers are adapters.

Required:
- validate input
- resolve actor/context
- call one service or facade
- map results to transport output

Not allowed:
- opening sessions directly in route files
- calling provider adapters directly from routes
- touching `app.state.container` except through thin dependency helpers
- reaching into private service fields such as `service._workflow` or `service._repo`

### 5. Workflow Policy
Use workflows only for real orchestration.

Use a workflow when logic:
- spans multiple application services
- includes retries, compensation, cancellation, or resumability
- coordinates provider calls and persistence across steps

Do not put trivial one-step logic into `workflows/`.
Do not let workflow helpers become a second service layer with no clear ownership.

### 6. Testability Policy
Every major collaborator must be replaceable without patching private fields.

Required:
- constructor injection or bootstrap override hooks
- fake implementations for ports
- deterministic seams for providers and background execution

Not allowed:
- tests mutating private attributes to replace providers
- tests relying on container internals that normal application code should not know about

### 7. Observability Policy
Background execution, orchestration, and provider calls must be observable.

Required:
- structured logging
- request and trace correlation
- persisted or exported workflow/provider events
- explicit handling of background task failure

Not allowed:
- swallowing background errors silently
- hidden long-running execution with no task id, log context, or failure signal

## Canonical Backend Shape

Preferred backend layout:

```text
backend/
├── pyproject.toml
├── alembic.ini
├── alembic/
├── src/
│   └── {package}/
│       ├── app.py
│       ├── modules/
│       │   └── {module}/
│       │       ├── __init__.py
│       │       ├── bootstrap.py
│       │       ├── domain/
│       │       │   ├── __init__.py
│       │       │   ├── entities.py
│       │       │   ├── value_objects.py
│       │       │   └── exceptions.py
│       │       ├── use_cases/
│       │       │   ├── __init__.py
│       │       │   ├── commands.py
│       │       │   ├── views.py
│       │       │   ├── ports.py
│       │       │   └── {module}_service.py
│       │       ├── workflows/
│       │       │   ├── __init__.py
│       │       │   └── {workflow}.py
│       │       ├── infra/
│       │       │   ├── __init__.py
│       │       │   ├── persistence.py
│       │       │   ├── queries.py
│       │       │   ├── providers.py
│       │       │   └── realtime.py
│       │       └── models.py
│       ├── entrypoints/
│       │   └── http/
│       ├── platform/
│       │   ├── composition/
│       │   ├── config/
│       │   ├── db/
│       │   ├── observability/
│       │   ├── providers/
│       │   ├── tasks/
│       │   └── workflows/
│       └── shared/
└── tests/
```

## Layer Rules

### Domain
Allowed:
- entities
- value objects
- domain rules
- domain exceptions

Forbidden:
- ORM models
- request or response schemas
- sessions
- vendor SDKs
- imports from another module's internals

### Use Cases
Allowed:
- commands and views
- service classes
- port definitions
- application-level validation and orchestration

Forbidden:
- raw SQL
- ORM model manipulation
- HTTP concerns
- concrete provider SDK usage
- direct imports of infra implementations

### Workflows
Allowed:
- multi-step orchestration
- cancellation and retry handling
- provider and persistence coordination through services and ports

Forbidden:
- becoming the default home for ordinary business logic
- bypassing module services and writing directly to infra unless that is the workflow's explicit boundary

### Infra
Allowed:
- concrete repository implementations
- DB queries
- provider adapters
- realtime adapters
- serialization and mapping

Forbidden:
- owning business rules
- exposing unstable internal details as module public API

### Platform
Allowed:
- app configuration
- database engine and session setup
- composition root and module registration
- logging, tracing, metrics, error normalization
- background task execution
- orchestration runtime wrappers

Forbidden:
- embedding product-specific business behavior that belongs in a module

## Dependency Rules

Allowed direction:

```text
entrypoints -> module public API -> use_cases -> domain
entrypoints -> dependency helpers -> container interfaces
workflows -> use_cases -> domain
infra -> use_cases.ports + domain
platform -> infra + module bootstrap + shared
```

Not allowed:
- `domain -> use_cases`
- `domain -> infra`
- `use_cases -> concrete infra`
- `entrypoints -> platform.db.session`
- `entrypoints -> provider adapters`
- `module A -> module B internals`

## Module Public API

Every module exports a small public API from `modules/{module}/__init__.py`.

Public API may include:
- the main service or facade
- commands and views that are intentionally shared
- module bootstrap function

Public API must not include:
- concrete repositories
- SQL helpers
- provider adapters
- ORM models

## Composition Standard

The application must be assembled through small registrars, not one giant constructor file.

Preferred shape:

```text
platform/composition/
├── app_container.py
├── shared.py
├── providers.py
└── modules/
    ├── identity.py
    ├── practice.py
    └── assistant.py
```

Rules:
- each module bootstrap returns a typed bundle of public collaborators
- the top-level app container composes bundles, not module internals
- the app container may own lifecycle resources, but not business logic

## Background Task Standard

Background execution must be explicit and observable.

Required:
- a task runner interface
- structured error reporting for failed tasks
- cancellation on shutdown
- trace or request correlation

Preferred:
- task metadata object with task id, origin, and purpose
- persistent failure event or log record

## Stageflow Standard

Stageflow is an orchestration engine, not an application architecture.

Required:
- wrap Stageflow in `platform/workflows/`
- expose app-owned orchestration helpers to modules
- keep Stageflow-specific types at the workflow boundary where possible

Not allowed:
- making business services depend deeply on raw Stageflow internals unless the service is explicitly an orchestration service

## Testing Standard

Minimum expectations:
- unit tests for domain and use-case logic
- integration tests for persistence and wiring
- smoke tests for app startup and key provider/runtime paths

Architecture rule:
- tests should override collaborators via public seams
- if a test must patch a private attribute, that is a design smell and should trigger a refactor

## Shared vs Platform

Use `shared/` for cross-cutting code that is generic and domain-neutral.

Examples:
- base errors
- ID helpers
- typed primitives
- common protocol helpers

Use `platform/` for runtime infrastructure.

Examples:
- config loading
- DB session factories
- telemetry wiring
- task execution
- orchestration runtime

Do not put bounded-context logic in either `shared/` or `platform/`.

## Review Rejection Criteria

Reject a change if it:
- mixes sync blocking persistence into async request or workflow code
- adds direct route access to sessions, provider adapters, or container internals
- imports concrete infra into use cases
- exports infra from a module root
- introduces a god repository or god service
- introduces a god container
- requires tests to patch private fields to replace collaborators
- adds silent background failure paths

## Ongoing Guide For Adding New Content

### When adding a new module
- create the module with `domain`, `use_cases`, `infra`, and optional `workflows`
- add `bootstrap.py`
- define ports before infra implementations
- export only the intended public API

### When adding a new route
- add transport schema only if needed at the adapter boundary
- use dependency helpers to resolve the service
- do not open sessions directly in the route
- do not call provider clients directly in the route

### When adding a new provider integration
- add a provider port first
- implement the adapter in `infra/` or `platform/providers/`
- configure retries, timeouts, and observability at the adapter boundary
- keep provider-specific payload shapes out of domain code

### When adding a new workflow
- define why it belongs in `workflows/`
- make cancellation, retry, and failure semantics explicit
- ensure the workflow is testable without private patching

### When adding a generic agent capability
- keep runtime mechanics in `platform/agents/`
- keep public operational use cases in a module such as `modules/agent_runs/`
- keep Stageflow behind app-owned runtime contracts
- persist runs, turns, tool calls, and ordered events
- keep product-specific prompts, policies, and output shaping out of platform code
- follow [GENERIC_AGENT_PLAN.md](/home/antonioborgerees/coding/HelloSales/ops/GENERIC_AGENT_PLAN.md) as the implementation plan

### When adding persistence
- add ORM models only for persistence representation
- keep mapping in infra
- keep transactions and session ownership explicit
- prefer unit-of-work or repository boundaries over passing sessions through services

### When adding background execution
- use the task runner abstraction
- attach correlation metadata
- make failures visible
- document shutdown behavior

## Final Rule

The architecture is only real if the seams are enforced by code, composition, and tests.
If the guide and the implementation drift apart, fix the implementation or update the guide immediately.
