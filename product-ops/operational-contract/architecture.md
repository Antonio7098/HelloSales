# Architecture Contract

## Purpose
This contract defines the core architectural rules for backend code in this project.

It governs:
- layer boundaries
- dependency direction
- module public APIs
- composition structure
- adapter boundaries
- shared vs platform ownership

It does not own every operational concern.
Use the specialized contracts in `ops/operational-contract/` for failures, observability, testing, workflows, agents, and pre-brief scope.

## Scope
This contract applies when a change:
- adds or edits backend modules
- introduces new use cases, services, or adapters
- changes dependency wiring or composition
- changes public module boundaries
- adds new transport or orchestration entrypoints

## How To Use This Contract
Use this contract in three ways:
- during reasoning, map the applicable requirement IDs to the sprint scope
- during implementation, preserve the required boundaries and dependency direction
- during review, verify conformance using the evidence guidance in each requirement

## Requirement Index

| ID | Title | Applies To | Severity If Violated |
| --- | --- | --- | --- |
| ARCH-CORE-001 | Module boundaries must remain explicit | new or changed modules | High |
| ARCH-CORE-002 | Dependency direction must point inward | cross-layer dependencies | Blocker |
| ARCH-LAYER-001 | Domain layer must remain pure | domain code | High |
| ARCH-LAYER-002 | Use cases depend on ports, not infra | use cases and services | Blocker |
| ARCH-ENTRY-001 | Transport adapters must stay thin | routes, webhooks, sockets, CLI | High |
| ARCH-MODULE-001 | Module public APIs must stay small and stable | module exports | Medium |
| ARCH-COMP-001 | Composition must happen through registrars | composition root and bootstrap | High |
| ARCH-SHARED-001 | Shared and platform code must stay domain-neutral | shared and platform packages | High |

## Core Principles

1. One module equals one bounded context.
2. Dependency direction points inward toward business logic.
3. High-level policy depends on abstractions, not concrete infra.
4. Transport entrypoints are adapters, not business layers.
5. Infrastructure is replaceable.
6. Architectural seams must remain testable through public boundaries.

## Requirements

### ARCH-CORE-001: Module Boundaries Must Remain Explicit

**Rule**
Each backend module must represent a bounded context with a small public API and clear internal ownership.

**Applies when**
- creating a new module
- expanding an existing module
- exposing one module to another

**Required**
- keep module internals behind the module boundary
- export only intentional public collaborators from `modules/{module}/__init__.py`
- keep domain, use-case, infra, and optional workflow responsibilities distinct

**Forbidden**
- importing another module's internals directly
- exporting concrete infra from the module root
- mixing unrelated bounded contexts in one module

**Evidence**
- module imports flow through public module APIs
- module root exports remain small and intentional
- feature code does not reach into sibling module internals

### ARCH-CORE-002: Dependency Direction Must Point Inward

**Rule**
Dependency direction must point from outer layers toward inner business logic.

**Applies when**
- adding imports across layers
- introducing adapters or orchestration
- wiring dependencies in composition

**Required**
- `entrypoints -> module public API -> use_cases -> domain`
- `infra -> use_cases.ports + domain`
- `platform -> infra + module bootstrap + shared`

**Forbidden**
- `domain -> use_cases`
- `domain -> infra`
- `use_cases -> concrete infra`
- `entrypoints -> platform.db.session`
- `entrypoints -> provider adapters`

**Evidence**
- imports follow the allowed direction
- use cases rely on ports rather than concrete adapters
- transport code does not open direct infrastructure dependencies

### ARCH-LAYER-001: Domain Layer Must Remain Pure

**Rule**
Domain code must model business behavior and must not depend on transport, persistence, or vendor concerns.

**Applies when**
- editing `domain/`
- introducing domain entities, value objects, or exceptions

**Required**
- keep entities, value objects, domain rules, and domain exceptions in the domain layer
- keep domain logic independent from ORM, transport, and SDK details

**Forbidden**
- ORM models in domain code
- request or response schemas in domain code
- sessions or vendor SDK usage in domain code

**Evidence**
- domain imports remain infrastructure-free
- domain tests do not require transport or DB wiring

### ARCH-LAYER-002: Use Cases Depend On Ports, Not Infra

**Rule**
Use cases and workflows must depend on narrow ports rather than concrete repositories, sessions, or provider clients.

**Applies when**
- adding services or use cases
- adding repository/provider access
- introducing orchestration

**Required**
- define ports in `use_cases/ports.py` or equivalent application-layer contracts
- implement those ports in `infra/` or platform adapters
- inject implementations during composition

**Forbidden**
- importing concrete infra classes into use cases
- leaking platform DB models into use cases
- broad interfaces with unrelated capabilities

**Evidence**
- use-case constructors accept ports or facades
- fake implementations can replace collaborators through public seams

### ARCH-ENTRY-001: Transport Adapters Must Stay Thin

**Rule**
HTTP routes, webhooks, CLI handlers, and websocket handlers must remain transport adapters.

**Applies when**
- adding or editing entrypoints
- introducing request/response schemas
- wiring route dependencies

**Required**
- validate input at the adapter boundary
- resolve actor or context
- call one service or facade
- map results to transport output

**Forbidden**
- opening sessions directly in route files
- calling provider adapters directly from routes
- touching container internals except through thin dependency helpers
- reaching into private service fields such as `service._workflow` or `service._repo`

**Evidence**
- route code delegates to a service or facade
- infrastructure access stays outside transport files

### ARCH-MODULE-001: Module Public APIs Must Stay Small And Stable

**Rule**
Every module must expose a small, stable public API and keep unstable details internal.

**Applies when**
- exporting module collaborators
- sharing commands or views across modules

**Required**
- export the main service or facade when needed
- export intentionally shared commands and views only when needed
- export the module bootstrap function where appropriate

**Forbidden**
- exporting concrete repositories
- exporting SQL helpers
- exporting provider adapters
- exporting ORM models

**Evidence**
- module roots stay small
- shared callers depend only on stable public symbols

### ARCH-COMP-001: Composition Must Happen Through Registrars

**Rule**
Application assembly must happen through a composition root that composes module registrars instead of reaching into module internals.

**Applies when**
- wiring the app container
- adding modules to the app
- changing bootstrap behavior

**Required**
- keep top-level assembly in `platform/composition/`
- let each module own `bootstrap.py` or an equivalent registrar
- have the top-level container compose module bundles and shared platform services

**Forbidden**
- one god-object constructor that knows every internal detail in the system
- routes or external adapters reaching through the container into private service internals

**Evidence**
- modules expose typed bundles or public collaborators
- composition code depends on module bootstrap outputs, not module internals

### ARCH-SHARED-001: Shared And Platform Code Must Stay Domain-Neutral

**Rule**
`shared/` and `platform/` must remain free of bounded-context business behavior.

**Applies when**
- adding utilities to `shared/`
- adding runtime infrastructure to `platform/`

**Required**
- use `shared/` for generic cross-cutting code such as base errors, IDs, typed primitives, and protocol helpers
- use `platform/` for runtime infrastructure such as config, DB setup, telemetry wiring, task execution, and orchestration wrappers

**Forbidden**
- embedding bounded-context logic in `shared/`
- embedding product-specific business behavior in `platform/`

**Evidence**
- platform packages expose runtime services, not product policy
- shared packages remain reusable and domain-neutral

## Review Rejection Criteria
Reject a change if it:
- imports concrete infra into use cases
- adds direct route access to sessions, provider adapters, or container internals
- exports infra from a module root
- introduces a god repository, god service, or god container
- creates cross-module dependencies through private internals
- puts bounded-context behavior into `shared/` or `platform/`

## Related Contracts
- [errors.md](/home/antonioborgerees/coding/HelloSales/product-ops/operational-contract/errors.md)

- [observability.md](/home/antonioborgerees/coding/HelloSales/product-ops/operational-contract/observability.md)

- [testing.md](/home/antonioborgerees/coding/HelloSales/product-ops/operational-contract/testing.md)

- [workflows.md](/home/antonioborgerees/coding/HelloSales/product-ops/operational-contract/workflows.md)

- [llm.md](/home/antonioborgerees/coding/HelloSales/product-ops/operational-contract/llm.md)

- [pre-brief-scope.md](/home/antonioborgerees/coding/HelloSales/product-ops/operational-contract/pre-brief-scope.md)
