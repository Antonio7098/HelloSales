# Workflow Contract

## Purpose
This contract defines when workflows are justified and how orchestration boundaries must behave.

It governs:
- workflow eligibility
- orchestration ownership
- retry, cancellation, and compensation semantics
- workflow boundary design
- engine encapsulation
- workflow observability expectations

## Scope
This contract applies when a change:
- adds or edits a workflow
- introduces orchestration runtime integration
- coordinates multiple services or external systems across steps

## Requirement Index

| ID | Title | Applies To | Severity If Violated |
| --- | --- | --- | --- |
| WF-SCOPE-001 | Workflows must be used only for real orchestration | workflow additions | Medium |
| WF-BOUNDARY-001 | Workflow engines must stay behind app-owned boundaries | orchestration runtime integration | High |
| WF-STATE-001 | Workflow outcomes must be explicit and inspectable | workflow execution paths | High |
| WF-RETRY-001 | Retry and cancellation semantics must be explicit | long-running and retrying workflows | High |

## Requirements

### WF-SCOPE-001: Workflows Must Be Used Only For Real Orchestration

**Rule**
Workflows are for multi-step orchestration, not as a default home for ordinary business logic.

**Required**
- use workflows when logic spans multiple services or systems
- use workflows when retries, cancellation, compensation, or resumability matter

**Forbidden**
- moving trivial one-step logic into `workflows/`
- creating a second service layer with no clear ownership

**Evidence**
- workflow reasoning explains why orchestration is warranted
- ordinary business logic remains in domain or use-case layers

### WF-BOUNDARY-001: Workflow Engines Must Stay Behind App-Owned Boundaries

**Rule**
Workflow engine details must remain encapsulated behind app-owned runtime or facade boundaries.

**Required**
- wrap engine-specific integration in app-owned runtime helpers
- expose narrow orchestration contracts to modules

**Forbidden**
- making general business services depend deeply on raw engine internals without explicit orchestration ownership

**Evidence**
- modules depend on app-owned workflow helpers or protocols
- engine-specific types are contained at the orchestration boundary where possible

### WF-STATE-001: Workflow Outcomes Must Be Explicit And Inspectable

**Rule**
Workflow execution must end in explicit, inspectable state transitions.

**Required**
- make terminal outcome visible
- preserve step-level failure context when failures matter
- keep partial completion and inconsistent-state outcomes explicit

**Forbidden**
- ambiguous or hidden workflow terminal states
- silent step failure with implied success

**Evidence**
- workflow status or events expose terminal outcomes and failure detail

### WF-RETRY-001: Retry And Cancellation Semantics Must Be Explicit

**Rule**
Retry, cancellation, and compensation behavior must be defined rather than implied.

**Required**
- declare retryable conditions and attempt limits
- make cancellation and timeout behavior explicit
- define compensation expectations where partial completion matters

**Evidence**
- reasoning and implementation expose retry/cancellation semantics
- tests or runtime evidence cover important lifecycle behavior

## Review Rejection Criteria
Reject a change if it:
- adds a workflow for trivial one-step logic
- leaks engine internals across ordinary application surfaces
- leaves workflow terminal outcomes ambiguous
- introduces retries or cancellation with no explicit semantics
