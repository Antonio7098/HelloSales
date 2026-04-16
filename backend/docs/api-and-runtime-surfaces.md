# API And Runtime Surfaces

## Purpose
This document describes the backend's public HTTP surfaces and its most important internal runtime surfaces.

## HTTP API Surface

Top-level router:
- `src/hello_sales_backend/entrypoints/http/router.py`

Mounted route groups:

### `/health`
Purpose:
- liveness and readiness-style operational checks

### `/agent-runs`
Purpose:
- start an agent run
- append turns to a run
- inspect a run
- replay or observe run events
- decide approvals
- cancel a run

Backed by:
- `modules/agent_runs/use_cases/agent_run_service.py`
- `platform/agents/runtime.py`

### `/jobs`
Purpose:
- start lightweight operational jobs
- inspect job/task state

Backed by:
- `modules/jobs/use_cases/jobs_service.py`
- `platform/tasks/runner.py`
- `platform/workflows/executor.py`

### `/system`
Purpose:
- system status
- diagnostics snapshot

Backed by:
- `modules/system/use_cases/system_service.py`

## Internal Runtime Surfaces

### App Container
Primary runtime graph:
- `platform/composition/app_container.py`

This is the authoritative assembly point for the backend runtime.

### Startup Hooks
- `platform/composition/startup.py`

Owns:
- startup validation
- DB reachability check when applicable
- startup completion/failure logging
- startup operational event emission

### Provider Surface
- `platform/composition/providers.py`
- `platform/providers/llm/`

Current provider surface is centered on the shared LLM contract.

### Agent Runtime Surface
- `platform/agents/runtime.py`
- `platform/agents/persistence.py`
- `platform/agents/models.py`

This runtime owns:
- run state
- turn state
- tool-call state
- append-only event stream state
- approval pause behavior
- cancellation/completion/failure transitions

### Task Surface
- `platform/tasks/runner.py`
- `platform/tasks/models.py`

This runtime owns:
- task scheduling
- task snapshots
- task failure capture
- task cancellation
- task event persistence hook

### Observability Surface
- `platform/observability/runtime.py`
- `platform/observability/events.py`
- `platform/observability/middleware.py`
- `platform/observability/health.py`

This runtime owns:
- operational events
- alerts derived from severity/code
- request context correlation
- health metadata and readiness support

### Workflow Surface
- `platform/workflows/runtime.py`
- `platform/workflows/executor.py`
- `platform/workflows/registry.py`

This is the app-owned boundary around Stageflow.

## Main Data / Control Flows

### Request Flow

```text
HTTP route
-> dependency resolution
-> module service
-> platform/runtime collaborators
-> persistence / provider / workflow execution
-> transport response
```

### Agent Run Flow

```text
POST /agent-runs
-> AgentRunService.start_run()
-> persist run + first turn
-> BackgroundTaskRunner.start()
-> GenericAgentRuntime.process_turn()
-> persist tool calls + events + final run state
```

### Approval Flow

```text
approval decision endpoint
-> AgentRunService.decide_approval()
-> update tool-call approval state
-> reschedule turn if approved
-> finalize turn if rejected
```

### Job Flow

```text
POST /jobs...
-> JobsService.start_diagnostic_job()
-> BackgroundTaskRunner.start()
-> run_diagnostic_workflow()
-> WorkflowExecutor.run_diagnostic_workflow()
```

### Diagnostics Flow

```text
GET /system/...
-> SystemService
-> provider diagnostics + task diagnostics + agent diagnostics + events + alerts
-> consolidated operational view
```

## Extension Points

High-signal extension points today:
- add a new module under `modules/`
- add a new provider implementation under `platform/providers/`
- add a new agent definition under `application/agents/definitions/`
- add a new smoke suite under `smoke/suites/`
- extend diagnostics through `modules/system/`
- extend runtime assembly through `platform/composition/`

## Where To Start Reading

If you are new to the backend, the best reading order is:
1. `app.py`
2. `platform/composition/app_container.py`
3. `entrypoints/http/router.py`
4. `modules/system/use_cases/system_service.py`
5. `modules/jobs/use_cases/jobs_service.py`
6. `modules/agent_runs/use_cases/agent_run_service.py`
7. `platform/agents/runtime.py`
