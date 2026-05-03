# API And Runtime Surfaces

## Purpose
This document describes the backend's public HTTP surfaces and its most important internal runtime surfaces.

## HTTP API Surface

Top-level router:
- `src/hello_sales_backend/entrypoints/http/router.py`

Mounted route groups:

### `/auth`
Purpose:
- redirect to the configured hosted auth provider
- accept provider callbacks and establish the app session cookie
- expose the current authenticated session
- clear the app session and return the provider logout redirect

Backed by:
- `modules/auth/use_cases/auth_service.py`
- `platform/auth/`

Auth endpoints:
- `GET /auth/login`
- `GET /auth/callback`
- `GET /auth/session`
- `POST /auth/logout`

### `/health`
Purpose:
- liveness and readiness-style operational checks

### `/sessions`
Purpose:
- create a durable session
- append session messages
- inspect ordered session items
- replay or observe attached execution events
- decide approvals for attached agent execution
- cancel a session-backed conversation

Backed by:
- `modules/sessions/use_cases/session_service.py`
- `platform/sessions/`
- `modules/agent_runs/use_cases/agent_run_service.py`
- `platform/agents/runtime.py`

Authorization:
- requires `app.access`
- read operations require `sessions.read`
- write, approval, and cancellation operations require `sessions.write`
- elevated cross-session access uses `sessions.read:any` and `sessions.write:any`

### `/worker-runs`
Purpose:
- start a worker run
- inspect a worker run
- inspect worker events
- cancel a worker run

Backed by:
- `modules/worker_runs/use_cases/worker_run_service.py`
- `platform/workers/runtime.py`

Authorization:
- read operations require `workers.read`
- run creation requires `workers.run`
- cancellation requires `workers.cancel`

### `/jobs`
Purpose:
- start lightweight operational jobs
- inspect job/task state

Backed by:
- `modules/jobs/use_cases/jobs_service.py`
- `platform/tasks/runner.py`
- `platform/workflows/executor.py`

Authorization:
- read operations require `jobs.read`
- diagnostic job creation requires `jobs.run`

### `/system`
Purpose:
- system status
- diagnostics snapshot

Backed by:
- `modules/system/use_cases/system_service.py`

Authorization:
- requires `app.access`
- requires `system.read`

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
- `platform/auth/`
- `platform/llm/`

Current provider surface is centered on the neutral shared LLM contract.
Auth provider resolution follows the same app-owned composition pattern, with WorkOS as the first real adapter and a no-op provider for test/local assembly.

### Agent Runtime Surface
- `platform/agents/runtime.py`
- `platform/agents/persistence.py`
- `platform/agents/models.py`

This runtime owns:
- neutral session state
- append-only session chronology
- summary state and latest materialized session summary
- attached execution references

### Worker Runtime Surface
- `platform/workers/runtime.py`
- `platform/workers/persistence.py`
- `platform/workers/models.py`

This runtime owns:
- worker run state
- local structured-output validation
- retry and timeout behavior
- append-only event state
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
- metrics and tracing for HTTP, background tasks, and worker runs

### Workflow Surface
- `platform/workflows/runtime.py`
- `platform/workflows/executor.py`
- `platform/workflows/registry.py`

This is the app-owned boundary around Stageflow.

## Main Data / Control Flows

### Request Flow

```text
HTTP route
-> auth middleware resolves current session into request state
-> dependency resolution
-> permission dependency checks route capabilities
-> module service
-> platform/runtime collaborators
-> persistence / provider / workflow execution
-> transport response
```

### Session Flow

```text
POST /sessions
-> auth dependency validates app/session write permissions
-> SessionService.create_session()
-> persist session + first user message
-> AgentRunService.start_run(session_id=..., auth_context=...)
-> BackgroundTaskRunner.start()
-> GenericAgentRuntime.process_turn()
-> tool execution receives actor/org/permission snapshot
-> persist session items + events + final attached run state
```

### Worker Run Flow

```text
POST /worker-runs
-> WorkerRunService.start_run()
-> persist run
-> BackgroundTaskRunner.start()
-> optional WorkflowExecutor.run_worker_run_workflow()
-> WorkerRuntime.process_run()
-> persist worker events + final run state
```

### Approval Flow

```text
approval decision endpoint
-> SessionService.decide_approval()
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
-> provider diagnostics + task diagnostics + agent diagnostics + worker diagnostics + events + alerts
-> consolidated operational view
```

## Extension Points

High-signal extension points today:
- add a new module under `modules/`
- add a new auth provider implementation under `platform/auth/providers/`
- add a new provider implementation under `platform/llm/providers/`
- add a new agent definition under `application/agents/definitions/`
- add a new worker definition under `application/workers/definitions/`
- add a new smoke suite under `smoke/suites/`

Recent internal runtime surfaces added in Sprint 7:
- `modules/semantic_catalog/` for canonical shared schema metadata
- `modules/entity_operations/` for generic create/edit orchestration, context refs, and undo records
- extend diagnostics through `modules/system/`
- extend runtime assembly through `platform/composition/`

## Where To Start Reading

If you are new to the backend, the best reading order is:
1. `app.py`
2. `platform/composition/app_container.py`
3. `entrypoints/http/router.py`
4. `modules/system/use_cases/system_service.py`
5. `modules/jobs/use_cases/jobs_service.py`
6. `modules/sessions/use_cases/session_service.py`
7. `modules/worker_runs/use_cases/worker_run_service.py`
8. `platform/agents/runtime.py`
9. `platform/workers/runtime.py`
