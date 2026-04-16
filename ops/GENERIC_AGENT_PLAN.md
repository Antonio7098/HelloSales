# Generic Agent Plan

## Purpose
This document defines the recommended plan for adding a generic agent runtime to this project before the product brief is known.

The goal is to build durable scaffolding:
- reusable agent runtime mechanics
- clear boundaries between runtime and product policy
- persistence for runs, turns, tools, and events
- observable execution
- approval, cancellation, and resume seams

This is not a product-assistant spec.
It is the implementation plan for the first application-owned agent foundation.

Use [ARCHITECTURE_RULES.md](/home/antonioborgerees/coding/HelloSales/ops/ARCHITECTURE_RULES.md) for normative rules.
Use [APPLICATION_BLUEPRINT.md](/home/antonioborgerees/coding/HelloSales/ops/APPLICATION_BLUEPRINT.md) for the broader backend foundation.

## Why This Shape

This plan is based on three sources of truth:
- the Stageflow extraction note in `/home/antonioborgerees/coding/stageflow/ops/stageflow-extraction-tracking.md`
- the Stageflow agent documentation in `/home/antonioborgerees/coding/stageflow/docs/guides/agents.md`
- the existing Soft Skills implementation, which is a useful reference but already contains product-specific policy

The key conclusion is:
- Stageflow should own reusable runtime mechanics
- this application should own agent policy, persistence, approvals, projections, and final response shaping
- the first build should be one generic single-agent runtime, not a multi-agent system

That matches external guidance as well:
- OpenAI recommends starting with a single agent and adding tools incrementally: https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/
- Anthropic recommends using the simplest pattern that works and distinguishing workflows from full agents: https://www.anthropic.com/engineering/building-effective-agents

## Design Goals

The first generic agent must make these things easy:
- starting an agent run
- sending a turn to the run
- invoking a small set of controlled tools
- pausing for approval
- cancelling a run
- replaying what happened from persisted events
- testing the loop without real providers

The first generic agent must make these things hard:
- embedding product-specific prompt logic into platform code
- coupling route handlers to raw Stageflow internals
- mixing persistence, policy, tool execution, and transport concerns in one class
- building a multi-agent topology before the single-agent runtime is stable

## Core Architectural Decision

Build the agent system in three parts.

### 1. Reusable Runtime In `platform/agents/`
This layer owns runtime mechanics and generic contracts.

It should contain:
- run lifecycle orchestration
- provider invocation seam
- tool runtime seam
- approval seam
- cancellation seam
- event emission
- persistence ports and adapters
- Stageflow integration wrapper for the agent loop

It must not contain:
- sales-specific reasoning
- domain-specific prompts
- product-specific output formatting rules
- UI projection decisions

### 2. Application-Owned Agent Definitions In `application/agents/`
This layer owns concrete agent policy.

It should contain:
- agent registry
- named agent definitions
- per-agent prompts
- per-agent tool-selection policy
- per-agent tool bundles
- fallback response shaping

It must not contain:
- SQLAlchemy or persistence plumbing
- FastAPI request handling
- raw Stageflow runtime mechanics

### 3. Operational Module In `modules/agent_runs/`
This layer exposes the agent runtime as an application capability.

It should contain:
- use cases for starting runs and appending turns
- HTTP endpoints
- views for operational inspection
- module-local bootstrap wiring

It must not own concrete prompt or tool-selection policy.

## Recommended Filesystem Shape

```text
backend/src/{package}/
├── application/
│   ├── agents/
│   │   ├── contracts.py
│   │   ├── registry.py
│   │   ├── bootstrap.py
│   │   └── definitions/
│   │       ├── generic_agent/
│   │       │   ├── agent.py
│   │       │   ├── prompts.py
│   │       │   ├── policy.py
│   │       │   └── tools.py
│   │       └── observer_agent/
│   │           ├── agent.py
│   │           ├── prompts.py
│   │           ├── policy.py
│   │           └── tools.py
│   └── tools/
│       ├── system.py
│       └── jobs.py
├── modules/
│   └── agent_runs/
│       ├── __init__.py
│       ├── bootstrap.py
│       ├── use_cases/
│       │   ├── commands.py
│       │   ├── views.py
│       │   ├── ports.py
│       │   └── agent_run_service.py
│       ├── workflows/
│       │   └── generic_agent_workflow.py
│       └── infra/
│           ├── persistence.py
│           └── streaming.py
└── platform/
    └── agents/
        ├── __init__.py
        ├── config.py
        ├── models.py
        ├── runtime.py
        ├── persistence.py
        └── tools.py
```

## Runtime Ownership Boundaries

### `platform/agents/` Owns
- `AgentRuntimeConfig`
- `AgentRunContext`
- `AgentTurnInput`
- `AgentTurnResult`
- `AgentProjectionEvent`
- `AgentLoopPolicy`
- `AgentApprovalRequest`
- `AgentPersistencePort`
- `AgentEventStore`
- `AgentToolCatalog`
- Stageflow-backed loop execution helpers

### `application/agents/` Owns
- `AgentDefinition`
- `AgentRegistry`
- named agent ids such as `generic` and `observer`
- prompt builders
- tool-selection policy
- fallback response builders
- agent-specific tool bundles

### `application/tools/` Owns
- reusable business tool implementations
- cross-agent tool definitions
- capability-level tools such as runtime status, recent tasks, and diagnostic job start

### `modules/agent_runs/` Owns
- public application use cases
- operational command and view DTOs
- route dependencies
- module bootstrap
- any module-local query shaping for agent operations

### Future Product Modules Own
- domain prompts
- domain toolsets
- agent persona/policy variants
- workflow-specific result shaping
- realtime UX projection strategy

## SOLID Application To Agent Design

### Single Responsibility Principle
Split agent responsibilities aggressively.

Examples:
- one class for loop execution
- one collaborator for persistence
- one collaborator for tool execution
- one collaborator for approvals
- one collaborator for projection/event emission

Do not build a single `AgentService` that owns prompt rendering, LLM calls, tool dispatch, persistence, approvals, and streaming.

### Open/Closed Principle
The runtime must be extendable by:
- adding a new tool
- adding a new prompt profile
- adding a new approval policy
- adding a new persistence adapter
- adding a new provider adapter

Do not require broad edits across the loop every time a new tool or profile is introduced.

### Liskov Substitution Principle
Every provider adapter, approval adapter, and persistence adapter must preserve contract behavior.

Examples:
- all provider adapters must agree on tool-call and failure semantics
- all persistence adapters must agree on idempotent write behavior
- all approval adapters must agree on pending, approved, and rejected states

### Interface Segregation Principle
Keep ports narrow.

Prefer:
- `AgentRunReader`
- `AgentRunWriter`
- `AgentApprovalPort`
- `AgentToolExecutor`
- `AgentProjectionSink`

Avoid one broad `AgentInfrastructure` interface.

### Dependency Inversion Principle
The agent runtime must depend on ports for:
- model invocation
- persistence
- approvals
- time
- IDs
- event emission
- tool execution

It must not depend directly on SQLAlchemy sessions, FastAPI request objects, or vendor SDK clients.

## Persistence Plan

Set up operational persistence now.
Avoid domain persistence until the product brief exists.

Recommended first tables:
- `agent_runs`
- `agent_turns`
- `agent_tool_calls`
- `agent_artifacts`
- `agent_stream_events`

### `agent_runs`
Purpose:
- run identity
- status
- profile name
- actor metadata
- correlation ids
- started/completed timestamps
- failure summary

### `agent_turns`
Purpose:
- one persisted unit of user input or system continuation
- ordered turn sequencing
- prompt snapshot references if needed later
- final assistant response summary

### `agent_tool_calls`
Purpose:
- tool name
- arguments snapshot
- outcome status
- approval requirement
- execution timing
- normalized error payload

### `agent_artifacts`
Purpose:
- structured outputs that should survive beyond one response
- generated files
- extracted records
- workflow result payloads

### `agent_stream_events`
Purpose:
- append-only ordered event log for diagnostics and SSE replay
- lifecycle milestones
- tool start/completion
- approval pause/resume
- final answer emission

## Generic Tool Strategy

Start with a very small reusable application tool catalog.

Recommended first tools:
- `get_runtime_status`
- `list_recent_tasks`
- `get_task`
- `run_diagnostic_job`

These tools are low risk because they operate against system plumbing that already exists.
Do not add domain tools until the brief exists.

Implementation rule:
- tool execution contracts stay in `platform/agents/tools.py`
- reusable concrete tools live in `application/tools/`
- each agent definition assembles its own allowed tool bundle from those reusable tools

## Approval Strategy

Approval support should exist in the runtime from the start, even if the first approval policy is simple.

Required:
- tool calls can declare whether approval is required
- approval requests can be persisted
- runs can pause in a recoverable state
- approval decisions can resume execution idempotently

The initial approval adapter may be a simple persistence-backed manual approval mechanism exposed by HTTP.

## Streaming and Projection Strategy

Do not hardwire websocket or product-specific broker logic into the agent runtime.

Instead:
- persist ordered events in `agent_stream_events`
- expose SSE replay from the operational module
- keep projection sink abstractions narrow

This leaves room for a future realtime broker or UI event bus without rewriting the loop.

## Stageflow Integration Strategy

Use Stageflow as the loop engine, but keep the rest of the app dependent on app-owned contracts.

Stageflow should be responsible for:
- staged execution
- tool runtime integration
- provider-native tool calls where useful
- lifecycle hooks
- cancellation and hardening hooks

Application-owned runtime should be responsible for:
- run identity and correlation
- persistence
- approval pause/resume policy
- event normalization
- final answer shaping
- public APIs

## Initial Public API

Recommended first endpoints:
- `POST /api/agent-runs`
- `POST /api/agent-runs/{run_id}/turns`
- `GET /api/agent-runs/{run_id}`
- `GET /api/agent-runs/{run_id}/events`
- `POST /api/agent-runs/{run_id}/cancel`
- `POST /api/agent-runs/approvals/{approval_id}`

These are operational APIs.
They should stay intentionally narrow until the product brief exists.

## Implementation Order

### Phase 1. Runtime Contracts
Add:
- `platform/agents/config.py`
- `platform/agents/models.py`
- `platform/agents/tools.py`

Outcome:
- typed runtime model
- clear public seams
- no transport coupling

### Phase 2. Persistence
Add:
- SQLAlchemy ORM models
- Alembic migration
- SQLAlchemy stores for runs, turns, tool calls, and events

Outcome:
- durable operational history
- replayable execution trace

### Phase 3. Application Agent Registry
Add:
- `application/agents/contracts.py`
- `application/agents/registry.py`
- at least one concrete agent definition package
- reusable tool implementations under `application/tools/`

Outcome:
- concrete agent policy lives outside `platform`
- multiple agent profiles can be registered cleanly

### Phase 4. Runtime Execution
Add:
- Stageflow-backed generic loop runner
- provider integration through existing LLM port
- tool runtime integration
- event emission and logging

Outcome:
- single-agent loop works end to end

### Phase 5. Operational Module
Add:
- `modules/agent_runs/`
- module bootstrap
- use-case service
- routes and schemas

Outcome:
- the runtime becomes accessible through the app without leaking platform internals

### Phase 6. Second Concrete Agent
Add:
- one additional concrete agent profile with a different tool bundle or policy

Outcome:
- multi-profile support is proven rather than assumed

### Phase 7. Approval and Cancellation
Add:
- pause/resume support
- persisted approval requests
- cancellation endpoint and runtime hook

Outcome:
- safer execution model for future higher-risk tools

### Phase 8. Streaming
Add:
- SSE endpoint backed by persisted ordered events

Outcome:
- inspectable execution without committing to product-specific realtime architecture

### Phase 9. Tests
Add:
- unit tests for loop policy
- unit tests for tool execution semantics
- integration tests for persistence and restart/resume behavior
- smoke test for one full generic run

Outcome:
- the runtime can evolve without becoming fragile

## Acceptance Criteria

The generic agent foundation is good enough when:
- one run can be started and continued across multiple turns
- tool calls are persisted with status and timing
- every run has ordered events for replay and diagnostics
- approvals can pause and resume a run safely
- cancellation is explicit and observable
- tests can run with fake providers and fake tools
- HTTP routes remain thin adapters
- Stageflow internals do not leak across the application surface

## Deliberate Non-Goals For The First Iteration

Do not build these yet:
- multi-agent coordination
- planner-worker topologies
- domain-specific personas
- long-lived memory strategy beyond operational persistence
- broker-specific realtime UX projection
- complex prompt versioning UI
- autonomous tool discovery

The first goal is a reliable single-agent runtime with strong plumbing.

## Recommended Next Step

If this plan is accepted, the highest-signal next implementation sequence is:

1. create `platform/agents/` contracts and models
2. add the operational persistence schema and migration
3. build the SQLAlchemy stores and event model
4. add `modules/agent_runs/` with start-turn-inspect routes
5. wire one minimal Stageflow-backed generic agent loop
6. add approval and cancellation hooks
7. add SSE replay and tests

That sequence gives the project a strong agent foundation without prematurely committing to product behavior.
