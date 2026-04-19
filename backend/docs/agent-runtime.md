# Agent Runtime

## Purpose
This document explains how the implemented generic agent runtime works.

It focuses on:
- the architectural split between runtime mechanics, policy, and operational exposure
- run, turn, tool, and event lifecycle
- approvals, cancellations, and event replay
- how the LLM provider and tools are used

This document is intentionally conversational-only.
Structured workers now live in the separate worker runtime described in `worker-runtime.md`.

## Architectural Split

The current agent system is deliberately split into three layers.

### 1. Generic Runtime Mechanics
Location:
- `src/hello_sales_backend/platform/agents/`

Owns:
- runtime config
- runtime state models
- persistence contracts
- execution lifecycle
- tool execution context
- event append behavior

This layer should not own:
- concrete prompts
- product-specific policy
- route behavior
- application-level operational APIs

### 2. Application-Owned Agent Policy
Location:
- `src/hello_sales_backend/application/agents/`
- `src/hello_sales_backend/application/tools/`

Owns:
- concrete agent definitions
- agent registry assembly
- tool bundles and selection policy
- prompt-building and fallback response shaping

The current registry is assembled in:
- `application/agents/bootstrap.py`

The current concrete profiles are:
- `generic`
- `observer`

### 3. Operational Exposure Through A Module
Location:
- `src/hello_sales_backend/modules/agent_runs/`

Owns:
- public use cases for starting runs and appending turns
- approval decisions
- event inspection / observation
- cancellation
- transport-facing application facade for the agent system

This keeps transport and public operational behavior out of the generic runtime itself.

## Main Runtime Components

### `GenericAgentRuntime`
Location:
- `platform/agents/runtime.py`

Responsibilities:
- load the run and turn state
- mark lifecycle transitions
- execute a Stageflow-backed turn pipeline
- queue and execute tool calls
- pause when approval is required
- generate final response text
- mark success / failure / cancellation
- append stream events
- emit operational failure events
- emit agent execution metrics and tracing through the shared observability runtime

### `AgentRunService`
Location:
- `modules/agent_runs/use_cases/agent_run_service.py`

Responsibilities:
- create runs and turns
- schedule background execution through the task runner
- expose run details and event views
- decide approvals
- cancel active runs

### `AgentStorePort`
Location:
- `platform/agents/persistence.py`

Responsibilities:
- persist runs, turns, tool calls, and stream events
- provide sequence numbers for turns, tools, and events
- support approval lookups and event replay

## Core Lifecycle Model

The runtime tracks four related state machines.

### Run Lifecycle
A run is the top-level identity for one conversational execution thread.

A run records:
- profile name
- current status
- request / trace / actor metadata
- latest turn id
- terminal error summary when failed

### Turn Lifecycle
A turn is one input appended to a run.

A turn records:
- sequence number within the run
- input text
- response text
- current status
- error summary when failed

### Tool Call Lifecycle
A tool call is a persisted unit of tool execution inside a turn.

A tool call records:
- tool name
- arguments
- whether approval is required
- approval id when applicable
- result payload on success
- error summary on failure

### Event Stream Lifecycle
A run has an append-only ordered event stream.

Events record lifecycle milestones such as:
- turn started
- tool queued
- approval requested
- tool started
- tool completed
- tool failed
- turn awaiting approval
- turn completed
- turn failed
- run cancelled

This event stream supports diagnostics and replay.

## Turn Execution Flow

The normal flow is:

```text
AgentRunService.start_run() or append_turn()
-> persist run / turn
-> BackgroundTaskRunner.start()
-> GenericAgentRuntime.process_turn()
-> _mark_running()
-> resolve agent definition from registry
-> _run_pipeline()
```

The Stageflow-backed pipeline currently has three stages:

### `prepare_turn`
Responsibilities:
- inspect existing tool calls
- select tools for the turn if not already selected
- create persisted tool-call records
- emit queued and approval-requested events

### `execute_tools`
Responsibilities:
- stop early if an approval is still pending
- execute tools through the agent definition's tool bundle
- persist tool-call success or failure
- emit tool lifecycle events

### `generate_response`
Responsibilities:
- if approval is still pending, return approval state
- otherwise build prompt/messages from the agent definition
- call the configured LLM provider when available
- fall back to deterministic response generation when no real provider is configured

## Tool Model

Tools are selected by the agent definition's selection policy.

Each selected tool becomes a persisted `AgentToolCall` before execution.
That means tools are not transient hidden runtime steps; they are part of the durable execution record.

Tool execution uses:
- tool name
- structured arguments
- execution context containing request / trace / actor metadata

On success:
- tool result payload is persisted
- `agent.tool.completed` event is appended

On failure:
- failure is normalized to an `AppError` when necessary
- tool failure detail is persisted
- `agent.tool.failed` event is appended
- the turn ultimately fails unless the runtime explicitly handles the error

## Approvals

Approvals are first-class runtime state, not an afterthought.

When a tool requires approval:
- the tool call is persisted in `PENDING_APPROVAL`
- an approval id is assigned
- approval-requested events are appended
- the run and turn move to awaiting-approval state

Approval decisions happen through `AgentRunService.decide_approval()`.

### If approved
- tool-call status becomes approved
- run status returns to pending
- turn status returns to pending
- the turn is rescheduled through the task runner

### If rejected
- tool-call status becomes rejected
- the turn is completed with a rejection response
- the run is completed without executing the tool

## Cancellation

Cancellation is handled through `AgentRunService.cancel_run()`.

Behavior:
- appends a cancel-requested event
- asks the task runner to cancel the active task if present
- updates run and turn status to cancelled
- cancels any non-terminal tool calls if needed
- appends cancellation events

The runtime also handles `asyncio.CancelledError` inside `GenericAgentRuntime.process_turn()` and marks the run/turn cancelled.

## Provider Usage

The runtime uses the shared LLM provider from the app container.

Current provider behavior:
- if the provider is configured, the runtime uses it to generate a response after tool execution
- if the provider is not configured, the runtime uses the agent definition's fallback response builder

This allows:
- real-provider execution in supported environments
- deterministic scaffold-stage fallback behavior without hard failure for every local run

## Failure Philosophy

The agent runtime is designed so failures remain inspectable.

Important failure behaviors:
- tool failures are persisted on the tool call
- turn failures are persisted on the turn
- run failures are persisted on the run
- a stream event is appended for failure
- an operational event is emitted for run-level failure

This means you should be able to inspect a failed run through:
- run state
- turn state
- tool-call state
- stream event history
- operational events

## Agent Observability

The generic agent runtime now extends the shared platform observability runtime rather than introducing agent-local monitoring code.

Current agent telemetry includes:
- turn execution segment metrics for started, active, completed, failed, cancelled, and awaiting-approval outcomes
- tool-call metrics for approval requests, starts, completions, failures, and duration
- tracing spans for `agent_turn.execute` and `agent_tool.execute`
- correlation preservation through existing request and trace metadata

The term "execution segment" matters for approvals.
When a turn pauses for approval, the first runtime pass finishes with status `awaiting_approval`.
If that approval is later granted, the resumed execution creates a second execution segment for the same persisted turn.

The agent metrics are intentionally labeled only by low-cardinality fields:
- agent profile
- tool name
- terminal status

They intentionally do not label by:
- request id
- trace id
- run id
- turn id
- response text or raw tool output

## What To Read In Code

Best reading order:
1. `platform/agents/runtime.py`
2. `modules/agent_runs/use_cases/agent_run_service.py`
3. `application/agents/bootstrap.py`
4. `application/agents/registry.py`
5. `application/agents/definitions/`
6. `platform/agents/models.py`
7. `platform/agents/persistence.py`
