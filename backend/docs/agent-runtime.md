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
- profile-driven context assembly contracts and default sources
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

The current generic-agent tool bundle includes:
- `query_analytics_data`
- `create_entity`
- `edit_entity`
- `search_web`

The governed SQL tool is intentionally generic-agent-only in Sprint 5.
It is not registered on the observer profile.
The public web-search tool is also generic-agent-only in Sprint 6.
It is for current or public internet information, not private customer data or internal-only analytics.
Generic entity mutation tools were added in Sprint 7 and remain generic-agent-only with static approval required for every write.

Context policy is not owned by concrete agent definitions. The runtime receives a named context profile from composition and asks the platform context assembler to insert selected context around the concrete agent prompt.

### 3. Operational Exposure Through A Module
Location:
- `src/hello_sales_backend/modules/sessions/`
- `src/hello_sales_backend/modules/agent_runs/`

Owns:
- public use cases for session creation and append
- attached execution use cases for starting runs and appending turns
- approval decisions
- event inspection / observation
- cancellation
- transport-facing application facade for the session-backed agent system

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
- create attached runs and turns
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

### Public Web Search Tool Policy

`search_web` is a native tool backed by `modules/web_search.WebSearchService`.
The service returns normalized source objects and metadata only; it does not synthesize final answers.
The agent prompt instructs the model to use returned URLs for citation and to prefer governed SQL for approved internal analytics data.

The tool must not be used to send secrets, private customer data, confidential internal data, or internal-only analytics facts to a public search provider.
Approval is configurable with `HELLO_SALES_WEB_SEARCH_REQUIRES_APPROVAL`.

### Event Stream Lifecycle
A run has an append-only ordered event stream.

Events record lifecycle milestones such as:
- turn started
- context assembled
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
SessionService.create_session() or append_message()
-> persist session / user message
-> AgentRunService.start_run() or append_turn()
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

### Agent Loop
Responsibilities:
- if approval is still pending, return approval state
- build base prompt messages from the concrete agent definition
- assemble model-visible context through the configured context profile
- replay persisted provider tool-call messages explicitly
- call the configured LLM provider when available
- fall back to deterministic response generation when no real provider is configured

## Context Engineering

The context engine lives in:
- `platform/agents/context.py`

It defines:
- `AgentContextProfile` for named, versioned context policy
- `AgentContextSource` for replaceable session, memory, or retrieval sources
- `AgentContextBudget` for source-level message truncation
- provenance, skipped-source, and truncation metadata

The default composed profile is `basic-session-v1`.
It preserves the previous behavior:
- include a completed session summary as a system message
- keep the warning that summaries are historical context, not fresh evidence
- exclude session items covered by the summary
- include the last 16 eligible user, assistant, and tool-result items
- render recent tool results as compact JSON system context

Profile selection is controlled by `HELLO_SALES_AGENT_CONTEXT_PROFILE`, defaulting to `basic-session-v1`.
The default profile is assembled in the composition root with the current `SessionStorePort`.

The context event `agent.context.assembled` records profile id/version, source counts, skipped sources, truncation decisions, and provenance metadata. It deliberately does not include raw memory, retrieval, or prompt text.

Long-term memory and retrieval are represented as source seams only. The backend includes fake memory sources and a future retrieval port that accepts run/session/query metadata and returns ranked context blocks or refs; it does not implement vector stores, embeddings, chunking, indexing, or ranking.

## Tool Model

Tools are selected by the agent definition's selection policy.

Each selected tool becomes a persisted `AgentToolCall` before execution.
That means tools are not transient hidden runtime steps; they are part of the durable execution record.

Tool execution uses:
- tool name
- structured arguments
- execution context containing request / trace / actor metadata
- session / run / turn / tool-call correlation metadata when available

`query_analytics_data` is the first governed SQL tool in this runtime.
Its current policy is:
- static approval required before execution
- one semantic catalog selected by `catalog_id`
- one read-only SQL statement only
- approved relations and columns only
- bounded result rows and truncated cell values
- structured result metadata persisted with the tool result

On success:
- tool result payload is persisted
- `agent.tool.completed` event is appended

On failure:
- failure is normalized to an `AppError` when necessary
- tool failure detail is persisted
- `agent.tool.failed` event is appended
- the turn ultimately fails unless the runtime explicitly handles the error

`create_entity` and `edit_entity` now follow the same persisted lifecycle shape.
They differ in policy, not in runtime mechanics:
- both require approval
- `edit_entity` requires an opaque `entity_ref` plus `expected_version`
- both persist bounded redacted results rather than raw changed values
- both rely on module-owned validation and execution rather than runtime-owned heuristics

## Approvals

Approvals are first-class runtime state, not an afterthought.

When a tool requires approval:
- the tool call is persisted in `PENDING_APPROVAL`
- an approval id is assigned
- approval-requested events are appended
- the run and turn move to awaiting-approval state

Approval decisions happen through `AgentRunService.decide_approval()`.

The SQL tool deliberately uses the conservative path in Sprint 5.
Even safe aggregate queries pause for approval because dynamic approval policy has not been added to the runtime yet.

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
2. `modules/sessions/use_cases/session_service.py`
3. `modules/agent_runs/use_cases/agent_run_service.py`
4. `application/agents/bootstrap.py`
5. `application/agents/registry.py`
6. `application/agents/definitions/`
7. `platform/agents/models.py`
8. `platform/agents/persistence.py`
