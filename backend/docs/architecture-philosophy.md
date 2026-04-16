# Architecture Philosophy

## Purpose
This document explains the implemented architectural split of the backend and the philosophy behind it.

It is the codebase-level explanation of how the backend is organized today.
For normative must / must not rules, use the operational contracts.

## The Core Philosophy

The backend is organized around a small number of ideas:
- explicit composition
- thin transport adapters
- application capability modules
- runtime infrastructure isolated in platform packages
- replaceable seams for providers, workflows, and task execution
- operational visibility as a first-class concern

This is a scaffold-stage backend, so the architecture optimizes for:
- durable infrastructure before the product brief exists
- operational inspectability
- clean extension paths
- avoiding premature domain lock-in

## The Main Split

### `entrypoints/` = transport adapters
This layer owns HTTP-facing concerns.

It should stay thin.
Routes should resolve dependencies, call a module service, and translate the result into transport output.

### `modules/` = public application capability surfaces
This layer owns the application-facing capabilities exposed by the system.

Current modules are:
- `system`
- `jobs`
- `agent_runs`

A module is the right place for:
- public use cases
- command/view DTOs
- module-local bootstrap
- capability-specific orchestration through stable services

### `platform/` = runtime infrastructure
This layer owns runtime mechanics.

Current platform areas are:
- composition
- config
- db
- observability
- providers
- tasks
- workflows
- agents

This layer should provide runtime services, not product policy.

### `application/` = policy outside platform
This layer currently exists mostly for the agent system.

It owns:
- concrete agent definitions
- registry assembly
- reusable application-level tools

This is where policy lives when it should not be embedded into platform mechanics.

### `shared/` = reusable cross-cutting code
This layer owns shared helpers like:
- errors
- ids
- general reusable types/helpers

It should remain domain-neutral.

## Composition Root Philosophy

The composition root is the most important architectural anchor.

Location:
- `platform/composition/app_container.py`

It assembles the runtime graph once and then exposes the resolved services through a typed container.

This keeps wiring centralized while keeping module internals private.

The container currently assembles:
- settings
- database runtime
- provider registry
- observability runtime
- background task runner
- workflow runtime and executor
- agent runtime
- health service
- module registry

## Why Modules Exist

The modules are not just folders.
They are the stable application capability boundaries that sit between transport and runtime infrastructure.

### `system`
Provides an operator-facing view of runtime state.

### `jobs`
Provides operational jobs and diagnostic workflow execution.

### `agent_runs`
Provides the public operational interface for the generic agent runtime.

This means public HTTP behavior flows through module services rather than directly into platform runtime objects.

## Why Platform Services Exist

The platform packages isolate infrastructure that should remain reusable or replaceable.

Examples:
- provider registry isolates model-provider selection
- task runner isolates background scheduling and failure capture
- workflow runtime isolates Stageflow availability and execution boundary
- observability runtime isolates events and alerts

This lets the backend evolve without letting infrastructure details leak everywhere.

## Why The Agent System Is Split Further

The agent system has an extra split because it mixes runtime mechanics and policy if you are not careful.

So it is intentionally divided into:
- `platform/agents/` for mechanics
- `application/agents/` for concrete policy
- `modules/agent_runs/` for public operational exposure

That is one of the strongest architectural decisions in the current codebase.

## Operational-First Philosophy

This scaffold is deliberately stronger in operational behavior than in product domain behavior.

That means the codebase currently emphasizes:
- diagnostics
- event streams
- task lifecycle visibility
- approval boundaries
- health and readiness
- explicit startup validation
- smoke-verifiable runtime behavior

That is intentional because the scaffold is being built before the final brief.

## Extension Philosophy

The easiest safe extensions should be:
- adding a new module
- adding a new provider implementation
- adding a new agent definition
- adding a new smoke suite
- extending diagnostics
- extending composition with another runtime collaborator

The hardest changes should be:
- bypassing modules with transport-level business logic
- wiring directly into private runtime internals from routes
- mixing product policy into platform code
- hiding failures behind implicit fallbacks

## Current Architectural Character

The backend is best understood as:
- an operational scaffold
- with a composition-root-driven runtime graph
- exposing a few stable application capabilities
- ready for domain growth once the brief arrives

It is not yet a broad product-domain application.
That is by design.
