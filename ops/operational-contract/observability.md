# Observability Contract

## Purpose
This contract defines the minimum observability requirements for backend runtime behavior.

It governs:
- structured logging
- correlation and trace propagation
- operational event emission
- diagnostics surfaces
- health and readiness truthfulness
- background task visibility
- alert and metrics expectations

## Scope
This contract applies when a change:
- introduces a new failure path
- adds background execution or orchestration
- adds provider or dependency integration
- adds diagnostics, health, or monitoring surfaces
- changes runtime logging or event behavior

## How To Use This Contract
Use this contract to determine:
- what operational signals must exist
- what failures must be visible to operators
- what evidence review should expect for runtime observability

## Requirement Index

| ID | Title | Applies To | Severity If Violated |
| --- | --- | --- | --- |
| OBS-CORE-001 | Failures must produce structured operational signals | all operational failure paths | Blocker |
| OBS-CORR-001 | Correlation identifiers must survive subsystem boundaries | requests, tasks, workflows, provider calls | High |
| OBS-HEALTH-001 | Health endpoints must reflect operational truth | health/readiness surfaces | Blocker |
| OBS-DIAG-001 | Diagnostics surfaces must expose operator-relevant state | diagnostics endpoints and runtime state | Medium |
| OBS-BG-001 | Background work must have visible terminal state | task runners and background jobs | Blocker |
| OBS-ALERT-001 | High-severity signals must be machine-usable for alerting | events, metrics, alerts | Medium |

## Requirements

### OBS-CORE-001: Failures Must Produce Structured Operational Signals

**Rule**
Every meaningful failure path must emit a structured operational signal that operators can inspect.

**Applies when**
- handling request failures
- handling startup or shutdown failures
- handling provider, workflow, or persistence failures
- handling background task failures

**Required**
- emit structured logs with stable codes when failures occur
- emit operational events where the runtime supports them
- preserve enough redacted detail for debugging
- make the failure visible in at least one immediate channel and one durable or inspectable channel

**Forbidden**
- swallowing failures silently
- logging success when the operation actually failed or degraded
- returning empty success-shaped results to hide operational failure

**Evidence**
- log payloads contain stable codes and structured detail
- runtime events or equivalent operator-visible signals exist
- failure paths are observable in diagnostics, task state, or logs

### OBS-CORR-001: Correlation Identifiers Must Survive Subsystem Boundaries

**Rule**
Request, task, and workflow correlation identifiers must survive subsystem boundaries where safe and useful.

**Applies when**
- handling HTTP requests
- starting background tasks
- calling providers
- running workflows or orchestration

**Required**
- preserve request and trace identifiers across downstream calls where possible
- attach correlation metadata to background work and workflow execution
- include correlation identifiers in structured failures and events

**Forbidden**
- generating unrelated identifiers for the same runtime path without reason
- dropping correlation identifiers at subsystem transitions without justification

**Evidence**
- logs, events, and task records contain request or trace metadata
- diagnostics or task snapshots surface correlation fields

### OBS-HEALTH-001: Health Endpoints Must Reflect Operational Truth

**Rule**
Health and readiness surfaces must reflect whether the process can safely serve its intended workload.

**Applies when**
- implementing health endpoints
- changing dependency checks
- changing startup validation or readiness semantics

**Required**
- distinguish liveness from readiness
- fail readiness when required dependencies or required capabilities are unavailable
- represent degraded state when non-required capabilities are impaired

**Forbidden**
- returning healthy only because the process is alive
- masking required dependency failure behind optimistic health output

**Evidence**
- health handlers distinguish `live`, `ready`, and `degraded` or equivalent states
- readiness changes when required dependencies fail

### OBS-DIAG-001: Diagnostics Surfaces Must Expose Operator-Relevant State

**Rule**
The system must expose a stable diagnostics surface for in-process operational inspection.

**Applies when**
- adding diagnostics endpoints
- introducing operational state worth inspecting
- adding new runtime subsystems

**Required**
- centralize diagnostics rather than scattering hidden debug endpoints
- expose recent or current state that helps inspect operational behavior
- extend the canonical diagnostics surface when new operational state is introduced

**Forbidden**
- subsystem-specific hidden debug routes with no canonical operator path
- diagnostics that omit critical recent failure state

**Evidence**
- a canonical diagnostics surface exists
- new operational state is inspectable through that surface or explicitly justified elsewhere

### OBS-BG-001: Background Work Must Have Visible Terminal State

**Rule**
Background work must be owned, observable, and end in an explicit terminal state.

**Applies when**
- spawning tasks
- scheduling jobs
- adding asynchronous worker behavior

**Required**
- assign task identity and purpose metadata
- persist or expose task status transitions
- capture failure detail with stable codes where possible
- cancel or reconcile outstanding work on shutdown

**Forbidden**
- fire-and-forget work with no owner or task id
- tasks whose failures exist only in stdout
- ambiguous task end states

**Evidence**
- task records or snapshots show lifecycle transitions
- failed tasks surface terminal details for review and diagnostics

### OBS-ALERT-001: High-Severity Signals Must Be Machine-Usable For Alerting

**Rule**
Operational signals should be machine-usable for metrics and alerting rather than free-form text matching.

**Applies when**
- emitting operational events
- defining high-severity codes
- adding metrics or alert integrations

**Required**
- use stable codes for alertable failures
- preserve structured severity and component fields
- keep alerting and metrics code-driven where possible

**Forbidden**
- relying only on prose log messages for alerting
- collapsing unrelated failures into one uninformative code

**Evidence**
- emitted events include stable code, severity, and component fields
- metrics and alert rules can key off machine-readable fields

## Review Rejection Criteria
Reject a change if it:
- introduces a new failure path with no structured operational signal
- drops correlation identifiers across a meaningful boundary without reason
- makes readiness optimistic when required dependencies are unavailable
- launches background work with no visible terminal status
- relies on unstructured text instead of machine-readable failure metadata for operator-critical behavior
