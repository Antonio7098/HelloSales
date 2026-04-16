# Agent Contract

## Purpose
This contract defines the architectural boundaries for agent runtime capabilities.

It governs:
- runtime versus policy ownership
- tool execution boundaries
- persistence and event expectations
- approval, cancellation, and resume seams
- operational exposure of agent behavior

## Scope
This contract applies when a change:
- adds or edits agent runtime behavior
- adds concrete agent definitions or policies
- adds agent tools, approvals, or streaming behavior
- exposes agent capabilities through application modules or transport adapters

## Requirement Index

| ID | Title | Applies To | Severity If Violated |
| --- | --- | --- | --- |
| AGENT-BOUNDARY-001 | Runtime mechanics and policy must stay separate | agent runtime and definitions | High |
| AGENT-TOOL-001 | Tool execution boundaries must stay explicit | tools and tool runtime | High |
| AGENT-RUN-001 | Runs and events must be persisted or inspectable | agent runtime state | High |
| AGENT-LIFECYCLE-001 | Approval, cancellation, and resume seams must stay explicit | lifecycle controls | Medium |
| AGENT-EXPOSE-001 | Operational exposure must flow through application modules | routes and operational APIs | High |

## Requirements

### AGENT-BOUNDARY-001: Runtime Mechanics And Policy Must Stay Separate

**Rule**
Reusable runtime mechanics must remain separate from concrete agent policy.

**Required**
- keep generic runtime mechanics in runtime-focused packages
- keep concrete prompts, policy, and output shaping outside generic runtime code
- keep agent-specific behavior out of generic runtime classes

**Forbidden**
- embedding concrete prompt or policy logic in generic runtime packages
- bypassing the application registry with ad hoc route-level wiring

**Evidence**
- runtime packages expose mechanics and contracts
- concrete agent definitions live outside the generic runtime layer

### AGENT-TOOL-001: Tool Execution Boundaries Must Stay Explicit

**Rule**
Tool execution must occur through explicit contracts and allowed tool bundles.

**Required**
- keep tool runtime seams explicit
- keep reusable tool implementations separate from runtime mechanics
- keep per-agent tool selection policy explicit

**Forbidden**
- hidden tool execution behavior inside transport or unrelated business code
- agent-specific tool behavior hardwired into the generic runtime

**Evidence**
- allowed tool bundles are inspectable
- tool execution contracts are represented explicitly in code

### AGENT-RUN-001: Runs And Events Must Be Persisted Or Inspectable

**Rule**
Agent runs, turns, tool calls, and important lifecycle events must be durable or at least inspectable through a stable operational surface.

**Required**
- preserve run identity and lifecycle state
- preserve ordered events or equivalent replayable state
- preserve failure and tool execution context where relevant

**Evidence**
- run state and event history are available for diagnostics or operational inspection

### AGENT-LIFECYCLE-001: Approval, Cancellation, And Resume Seams Must Stay Explicit

**Rule**
Approval, cancellation, and resume behavior must be explicit from the start when those capabilities exist.

**Required**
- keep approval requests inspectable
- keep cancellation explicit and observable
- make resume semantics idempotent where relevant

**Forbidden**
- hidden pause or resume behavior with no durable state

**Evidence**
- lifecycle actions have explicit state transitions and operator-visible traces

### AGENT-EXPOSE-001: Operational Exposure Must Flow Through Application Modules

**Rule**
Agent runtime capabilities must be exposed through application modules rather than directly from platform runtime internals.

**Required**
- expose public use cases through an application module
- keep routes and transport concerns as adapters over that module

**Forbidden**
- transport code reaching directly into generic runtime internals
- platform runtime code owning public product or operational API behavior

**Evidence**
- public agent capability flows through module use cases and bootstrap wiring

## Review Rejection Criteria
Reject a change if it:
- mixes agent runtime mechanics with concrete policy logic
- hardwires tool behavior into generic runtime classes
- exposes agent runtime directly from transport adapters
- introduces approval or cancellation behavior with no explicit lifecycle state
