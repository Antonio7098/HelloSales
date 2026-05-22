# Sprint Reasoning: Runtime Unification

> Project: HelloSales
> Sprint ID: sprint-12-runtime-unification
> Created: 2026-05-03
> Output: `ops/sprints/sprint-12-runtime-unification/reasoning.md`

## Overview

**Sprint:** Runtime Unification
**Purpose:** Generalize sessions from conversational threads into durable activity timelines, and converge agent runs, worker runs, task ownership, events, and persistence around a cleaner execution substrate.
**Tracker:** To be created before execution. This reasoning uses the user-approved Sprint 12 scope: unify the currently convoluted session/agent/worker execution model.
**Depends On:** `sprint-02-worker-runtime-foundation`, `sprint-04-session-substrate-foundation`, `sprint-09-context-engineering`, `sprint-10-rag-primitives`, `sprint-11-voice-primitives`

Sprint 12 should make the system more elegant without flattening useful runtime semantics. The target abstraction is:

- **Session:** optional durable activity timeline, not necessarily a conversation.
- **Execution run:** durable execution owner for agent, worker, workflow, voice, or future runtime work.
- **Task:** infrastructure execution handle for in-process/background ownership, not the authoritative domain lifecycle.
- **Mode details:** agent turns, tool calls, approvals, worker attempts, and structured outputs remain explicit where their semantics matter.

## Requirement Map

### Contracts Reviewed For This Sprint

| Contract File | Area | Applicability | Why It Matters |
| --- | --- | --- | --- |
| `ops/operational-contract/architecture.md` | Layering and module boundaries | Applicable | The sprint changes core runtime boundaries, persistence, composition, and public module APIs. |
| `ops/operational-contract/errors.md` | Failure shape and terminal state | Applicable | Runtime unification must not hide orphaned runs, background failures, persistence failures, or cancellation. |
| `ops/operational-contract/observability.md` | Correlation and diagnostics | Applicable | Runs, sessions, events, and tasks need one inspectable operational story. |
| `ops/operational-contract/testing.md` | Unit, integration, smoke evidence | Applicable | Persistence and lifecycle changes require deterministic tests and runtime smoke coverage. |
| `ops/operational-contract/workflows.md` | Orchestration boundaries | Applicable | Worker direct vs Stageflow execution currently branches at runtime and must remain explicit. |
| `ops/operational-contract/llm.md` | Agent/worker lifecycle and prompt evidence | Applicable | Agent and worker execution are LLM-backed and must keep mode-specific policy visible. |
| `ops/operational-contract/pre-brief-scope.md` | Product-neutral foundation | Applicable | This is foundation work and must not invent product-specific session or workflow concepts. |
| `ops/operational-contract/frontend.md` | Frontend boundaries | Non-Applicable unless frontend is touched | Sprint 12 should be backend/runtime-first; any UI change must use typed feature-owned API seams. |
| Python contract modules under `backend/src/hello_sales_backend/**/contracts.py` | Runtime/provider code contracts | Applicable where touched | Agent, worker, LLM, voice, web search, auth, and smoke contracts define public seams that must remain stable or migrate intentionally. |

### Requirement Index Used In This Sprint

| Requirement ID | Title | Area | Applicability | Why It Matters For This Sprint |
| --- | --- | --- | --- | --- |
| ARCH-CORE-001 | Module boundaries must remain explicit | Architecture | Applicable | Execution substrate must not become a god module that absorbs sessions, agents, workers, and tasks without clear ownership. |
| ARCH-CORE-002 | Dependency direction must point inward | Architecture | Applicable | Use cases must depend on ports and public facades, not concrete SQL/task/runtime internals. |
| ARCH-LAYER-002 | Use cases depend on ports, not infra | Architecture | Applicable | Unified persistence and run orchestration need injectable stores/fakes. |
| ARCH-ENTRY-001 | Transport adapters must stay thin | Architecture | Applicable | Session, agent, and worker routes should remain facade calls only. |
| ARCH-MODULE-001 | Module public APIs must stay small and stable | Architecture | Applicable | Existing agent/worker/session APIs need backward-compatible facades during migration. |
| ARCH-COMP-001 | Composition must happen through registrars | Architecture | Applicable | App container wiring currently knows too much and always uses `InMemoryWorkerStore`; Sprint 12 must improve this without route-level coupling. |
| ARCH-SHARED-001 | Shared and platform code must stay domain-neutral | Architecture | Applicable | A generic run/session substrate belongs in platform only if it remains product-neutral. |
| ERR-CORE-001 | No failure may disappear | Errors | Applicable | Unified lifecycle must preserve terminal failure for orphaned runs, failed tasks, retries, and persistence errors. |
| ERR-SHAPE-001 | Operational errors must preserve canonical shape | Errors | Applicable | Migration and runtime failures need stable codes/details. |
| ERR-CODE-001 | Error codes must be stable and machine-usable | Errors | Applicable | New execution/session errors need specific codes, not generic `internal`. |
| ERR-TRANS-001 | Error translation must preserve cause and context | Errors | Applicable | Runtime, task, workflow, and store boundary errors must keep cause and ids. |
| ERR-RETRY-001 | Retryable errors must use explicit bounded policy | Errors | Applicable | Worker retry and agent LLM retry must survive unification without hidden retry loops. |
| ERR-BG-001 | Background work must end in explicit inspectable failure state | Errors | Applicable | Task/run drift is a current design pressure point. |
| ERR-DATA-001 | Persistence and data failures must be loud and distinct | Errors | Applicable | Worker runs are currently in-memory only; SQL persistence and migrations must fail loudly. |
| ERR-REDACT-001 | Redaction must protect secrets without destroying diagnosis | Errors | Applicable | Unified events may contain prompt, input, tool, worker, and provider metadata. |
| OBS-CORE-001 | Failures must produce structured operational signals | Observability | Applicable | Unified runs should make failure visible in events, state, and diagnostics. |
| OBS-CORR-001 | Correlation identifiers must survive subsystem boundaries | Observability | Applicable | `request_id`, `trace_id`, `actor_id`, `session_id`, `run_id`, `task_id`, and prompt refs must stay connected. |
| OBS-DIAG-001 | Diagnostics surfaces must expose operator-relevant state | Observability | Applicable | Diagnostics should expose sessions, runs, active tasks, orphan reconciliation, and recent terminal failures coherently. |
| OBS-BG-001 | Background work must have visible terminal state | Observability | Applicable | Task snapshots and durable run state must reconcile rather than disagree silently. |
| TEST-SEAM-001 | Collaborators must be replaceable through public seams | Testing | Applicable | New stores, orchestrators, and adapters need fakeable ports. |
| TEST-UNIT-001 | Business logic must have unit coverage | Testing | Applicable | Status mapping, event mapping, and attachment policy are deterministic logic. |
| TEST-INT-001 | Wiring and persistence changes need integration coverage | Testing | Applicable | SQL worker persistence, migrations, and composition changes require integration tests. |
| TEST-SMOKE-001 | Critical runtime paths must have smoke coverage | Testing | Applicable | Existing agent/session/worker smokes must pass after migration. |
| TEST-FAIL-001 | Failure paths must be tested explicitly | Testing | Applicable | Orphan recovery, cancellation, task failure, persistence failure, and retry exhaustion need negative coverage. |
| TEST-DET-001 | Tests must remain deterministic | Testing | Applicable | Runtime tests should assert stable state/events, not LLM prose. |
| WF-SCOPE-001 | Workflows only for real orchestration | Workflows | Applicable | Stageflow remains an execution mode, not a reason to force all runs through workflow machinery. |
| WF-BOUNDARY-001 | Workflow engines stay behind app boundaries | Workflows | Applicable | Unified run APIs must not leak Stageflow internals. |
| WF-STATE-001 | Workflow outcomes explicit and inspectable | Workflows | Applicable | Workflow-backed worker runs need explicit final run and task state. |
| WF-RETRY-001 | Retry and cancellation semantics explicit | Workflows | Applicable | Cancellation must reconcile run/task/workflow state. |
| LLM-BOUNDARY-001 | Shared substrate and mode-specific policy separated | LLM Runtime | Applicable | A unified run substrate must not merge conversational and structured policy into one opaque runtime. |
| LLM-TOOL-001 | Tool execution boundaries explicit and mode-scoped | LLM Runtime | Applicable | Agent tool calls and approvals must remain explicit after unification. |
| LLM-IO-001 | Structured input/output boundaries explicit | LLM Runtime | Applicable | Worker schemas and validation must remain authoritative. |
| LLM-LIFECYCLE-001 | Lifecycle controls explicit and inspectable | LLM Runtime | Applicable | Approval, resume, cancellation, timeout, fallback, and retry must remain visible. |
| LLM-RETRY-001 | LLM retry policy shared, bounded, inspectable | LLM Runtime | Applicable | Worker and agent retry behavior must remain mode-aware. |
| LLM-RUN-001 | Runs and events durable or inspectable | LLM Runtime | Applicable | This is the central Sprint 12 requirement. |
| LLM-PROMPT-001 | Prompt version propagation observable | LLM Runtime | Applicable | Unified runs must preserve prompt references for agents and workers. |
| LLM-EXPOSE-001 | Operational exposure through application modules | LLM Runtime | Applicable | Routes should not expose platform runtime internals directly. |
| LLM-OBS-001 | Monitoring uses canonical observability runtime | LLM Runtime | Applicable | Unified execution should reduce parallel telemetry, not add another stack. |
| PRE-SCOPE-001 | Foundation work may proceed before the brief | Pre-Brief | Applicable | Runtime unification is generic foundation work. |
| PRE-SCOPE-002 | Product-specific commitments wait for the brief | Pre-Brief | Applicable | Do not encode sales-specific session kinds, jobs, or workflows. |
| PRE-SCOPE-003 | Favor operational scaffolding over assumptions | Pre-Brief | Applicable | The sprint should improve seams, durability, and observability. |
| PRE-SCOPE-004 | Public APIs remain narrow | Pre-Brief | Applicable | Preserve existing APIs and add generic/internal surfaces only where needed. |
| FE-* | Frontend requirements | Frontend | Non-Applicable unless frontend changes | No frontend implementation is required for the runtime unification sprint. |

### Applicable Requirements

- **ARCH-CORE-001 / ARCH-MODULE-001:** The new substrate must have a small, explicit public API. It should not become a generic dumping ground for all runtime behavior.
- **ARCH-LAYER-002 / TEST-SEAM-001:** Use cases should depend on narrow store/orchestrator ports. Agent and worker tests must replace stores and runtimes without private patching.
- **ARCH-COMP-001 / ERR-DATA-001:** Composition must stop wiring workers to `InMemoryWorkerStore()` for all database configurations. Worker run durability must match agent/session durability.
- **ERR-BG-001 / OBS-BG-001 / LLM-RUN-001:** Background task state and durable run state must reconcile explicitly. The current orphan recovery logic is a symptom to design around.
- **LLM-BOUNDARY-001 / LLM-TOOL-001 / LLM-IO-001:** Unification should share identity, persistence, lifecycle, and events, but keep agent turns/tool calls and worker schemas/attempts mode-specific.
- **OBS-CORR-001 / LLM-PROMPT-001:** Unified run records must retain request, trace, actor, session, task, and effective prompt references.
- **PRE-SCOPE-002 / PRE-SCOPE-004:** Session kinds and item types must remain generic; do not invent product-specific activity types.

### Non-Applicable Requirements

- **FE-STRUCT-001 through FE-EXT-001:** Not applicable unless Sprint 12 adds frontend surfaces. If a UI is later added, it must be feature-owned with typed API access.
- **Provider-specific parts of ERR-PROVIDER-001:** No new external provider integration is planned. Existing LLM provider failure classification still applies to agent/worker execution.
- **Voice-specific Python contracts:** `platform/voice/contracts.py` was reviewed; Sprint 12 should not change voice provider semantics unless voice runs are later attached to the unified execution substrate.
- **Auth provider contract:** Reviewed and not directly changed. Auth context propagation remains relevant through existing `AuthContext` fields.

### Ambiguous Or Conflicting Requirements

- **Session as lifecycle owner vs run as lifecycle owner:** Current code marks sessions `COMPLETED`, `FAILED`, or `CANCELLED` based on attached agent execution. A generalized session may contain multiple runs, so session status cannot always mirror one latest run.
- **Generic run vs mode-specific run records:** LLM-RUN-001 pushes toward one durable run story, while LLM-BOUNDARY-001 requires conversational and structured policy to remain separate. The likely answer is a shared execution envelope with mode-specific detail records.
- **Task identity mapping:** Agent turns currently use `task_id=run.run_id`; workers generate a separate task id and store it on `WorkerRun`. A unified model must choose one consistent mapping or explicitly support both.
- **Backward compatibility vs elegance:** Existing routes and smokes likely depend on `/sessions`, `/agent-runs`, and `/worker-runs` shapes. Sprint 12 should improve internals without forcing a broad client break unless explicitly approved.

### Open Questions

- Should Sprint 12 include the SQL migration for unified execution records, or first add compatibility views over existing tables?
- Should the existing `AgentRun` and `WorkerRun` tables remain as mode-detail tables, or be migrated into one `execution_runs` table plus detail tables?
- Should `Session.latest_run_id` become `latest_execution_id`, remain as a compatibility alias, or be replaced by a query over session items?
- Should one-off worker and agent runs default to `session_id=None`, or should the service create an implicit general session for every run?
- What API versioning tolerance exists for changing response field names such as `latest_run_id`?

## Current Research

**Research Status:** External research not needed for this reasoning document.

This sprint is a local architecture and persistence refactor governed by the repository contracts and current code. No new external provider, framework, or protocol choice is being introduced. The relevant current guidance is already encoded in the operational contracts, especially the architecture, errors, observability, workflows, testing, and LLM runtime contracts.

### Sources Consulted

- `ops/process/reasoning/reasoning-protocol.md`: Procedure for this artifact.
- `ops/process/reasoning/reasoning-template.md`: Document shape and required sections.
- All files in `ops/operational-contract/`: Normative requirement source.
- Python contracts under `backend/src/hello_sales_backend/**/contracts.py`: Public runtime/provider seams.
- Existing session, agent, worker, task, persistence, runtime, and composition code listed in the feature analysis.

### Relevant Current Guidance

- The repository contracts require durable or inspectable LLM-backed runs, explicit background terminal state, stable errors, and thin application/module boundaries.
- Existing local patterns favor module services, platform-owned runtime contracts, SQL stores for durable state, and composition through `platform/composition`.
- Current code already has useful mode-specific models; the problem is coordination and inconsistent persistence, not the existence of mode-specific concepts.

### Options Or Guidance Rejected

- **Use an external workflow engine as the universal execution model:** Rejected because WF-SCOPE-001 says workflows are for real orchestration, not ordinary business logic.
- **Collapse agents and workers into one runtime class:** Rejected because LLM-BOUNDARY-001 requires conversational and structured policy to remain separated where semantics differ.
- **Leave worker runs in memory and only document the caveat:** Rejected because ERR-BG-001 and ERR-DATA-001 forbid in-memory-only tracking for important background work.

### Impact On Reasoning

- The design should introduce a shared execution envelope and event model while preserving agent/worker-specific detail tables and services.
- Session should become optional and more general before adding more runtime modes.
- Persistence parity is a first-class deliverable, not cleanup.

## Existing Code Constraints

- `SessionService` is currently a conversational facade. `create_session()` always creates an `AgentRun`, and `append_message()` always appends an agent turn through `AgentRunService`.
- `Session` is called neutral, but its docstring says "conversation root" and `SessionItemType` is chat-oriented: user message, assistant message, tool call, tool result, system note.
- `SessionAttachmentStore` mirrors agent runtime activity back into sessions and sets `session.latest_run_id`, creating bidirectional coupling between session state and agent execution.
- `AgentRunService` schedules background work with `TaskMetadata(task_id=run.run_id, purpose="generic_agent_turn")`.
- `WorkerRunService` creates a separate `task_id`, writes it to `WorkerRun`, and branches between direct runtime execution and Stageflow workflow execution.
- `AgentRunService._recover_orphaned_run()` marks a run failed when the DB says `RUNNING` but the task runner has no running snapshot.
- `app_container.py` uses SQL stores for agents/sessions when not SQLite, but always wires `worker_store: WorkerStorePort = InMemoryWorkerStore()`.
- Agent and worker prompt contracts already expose `effective_prompt_ref()`. Unification must preserve prompt identity/version fields.
- Existing smoke suites cover session, agent, worker, and voice runtime paths and should remain the regression safety net.

## Feature Analysis

### Feature 1: Generalize Session Into Durable Activity Timeline

**Description:** Change the session concept from conversation-only to an optional generic activity timeline that can contain messages, runs, artifacts, approvals, notes, and errors.

**Affected Areas**

- `backend/src/hello_sales_backend/platform/sessions/models.py`
- `backend/src/hello_sales_backend/modules/sessions/use_cases/session_service.py`
- `backend/src/hello_sales_backend/platform/sessions/attachment.py`
- `backend/src/hello_sales_backend/platform/db/models.py`
- `backend/src/hello_sales_backend/platform/db/repositories.py`
- Session routes, views, tests, and smokes

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-SHARED-001 | Session substrate stays product-neutral | Session kinds and item types | Naming/import review |
| LLM-RUN-001 | Attached LLM runs remain inspectable | Session item links to runs/events | Session + run integration tests |
| OBS-CORR-001 | Session/run/task ids remain correlated | Session item metadata | Event and detail view assertions |
| PRE-SCOPE-002 | No product-specific activity types | Session item taxonomy | Review checklist |

**Current-System Analysis**

- The session model already has append-only `SessionItem` records with `run_id`, `turn_id`, `tool_call_id`, and prompt metadata. That is the right foundation.
- The restrictive part is service behavior and item taxonomy. `SessionService.create_session()` immediately creates an agent run, and item types assume chat messages.
- `SessionStatus` currently mirrors the latest attached agent state. That does not generalize to sessions with multiple runs or non-conversational activity.

**Options Considered**

- **Option A:** Keep `Session` as chat-only and add separate `Job`, `Workflow`, or `RunGroup` containers.
- **Option B:** Rename `Session` to `ActivityTimeline` everywhere in one breaking migration.
- **Option C:** Generalize `Session` in place with optional `session_kind`, generic item types, and backward-compatible conversational commands.

**Chosen Approach**

- Adopt Option C. Keep `Session` as the persisted/API term for now, but make it mean durable activity timeline. Add generic kinds and item types while preserving existing message item types as compatibility aliases or specialized message variants.

**Decision Justification**

- Option C minimizes API churn while fixing the conceptual model.
- Option A preserves current confusion and creates parallel containers.
- Option B may be cleaner long-term, but it is too disruptive for one sprint unless the client/API migration scope is explicitly approved.

**Execution Notes**

- Do not remove conversational endpoints at the start. Add lower-level generic session creation/attachment seams first.
- Session status should represent the timeline/container state, not blindly mirror the latest run once multiple runs are possible.
- `latest_run_id` should become compatibility metadata over a more general attached-run relationship.

**Expected Evidence**

- **Tests:** creating a general session without an agent run; attaching a worker or agent run; listing generic session items in sequence.
- **Runtime Evidence:** session detail shows item chronology with stable run references.
- **Review Checks:** no product-specific session kinds; existing conversational session smoke still passes.

---

### Feature 2: Introduce Shared Execution Run Envelope

**Description:** Add a durable execution envelope that represents common run identity, ownership, status, task linkage, prompt reference, correlation, and terminal error state for agents and workers.

**Affected Areas**

- New or revised platform execution models/contracts
- Agent and worker run models/stores/views
- SQL models and migrations
- Runtime diagnostics and events
- Existing `AgentRunService` and `WorkerRunService`

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| LLM-RUN-001 | Runs/events durable or inspectable | Shared execution envelope | Persistence and event tests |
| LLM-BOUNDARY-001 | Mode policy remains separate | Agent turns and worker attempts | Unit tests per mode |
| LLM-TOOL-001 | Agent tools remain explicit | Agent tool call detail records | Approval/tool regression tests |
| LLM-IO-001 | Worker schemas remain explicit | Worker input/output validation | Worker runtime tests |
| OBS-CORR-001 | Correlation metadata persists | Run/task/session fields | Detail view assertions |

**Current-System Analysis**

- `AgentRun` and `WorkerRun` duplicate identity, status, prompt, timing, actor, request, trace, error, and event concepts.
- Their differences are real: agents have turns/tool calls/approvals; workers have structured input/output, attempts, timeouts, provider/model output, and direct vs Stageflow execution.
- A shared envelope should not delete those differences. It should remove duplicated lifecycle plumbing and create one place for common execution truth.

**Options Considered**

- **Option A:** Replace `AgentRun` and `WorkerRun` with one large `ExecutionRun` containing every possible field.
- **Option B:** Add `ExecutionRun` as common envelope plus `AgentRunDetail` and `WorkerRunDetail` mode-specific records.
- **Option C:** Keep existing tables and only add adapter functions that map both into a common view.

**Chosen Approach**

- Prefer Option B if Sprint 12 includes migrations. Use Option C only as an interim compatibility layer if migration risk is too high.

**Decision Justification**

- Option B best satisfies LLM-RUN-001 and LLM-BOUNDARY-001 together: one lifecycle envelope, separate mode semantics.
- Option A becomes a sparse god record and weakens mode boundaries.
- Option C improves views but leaves duplicated persistence and lifecycle ownership unresolved.

**Execution Notes**

- Define a small shared status enum only for common lifecycle: pending, running, awaiting_input_or_approval, retrying, completed, failed, cancelled, timed_out.
- Map agent and worker statuses intentionally. Do not make lossy mappings where semantics differ.
- Preserve prompt references on the shared envelope or a normalized prompt snapshot table.

**Expected Evidence**

- **Tests:** status mapping; agent run creation; worker run creation; prompt ref propagation; terminal error propagation.
- **Runtime Evidence:** diagnostics can list active/recent runs across agent and worker modes.
- **Review Checks:** no mode-specific tool/schema policy in shared envelope code.

---

### Feature 3: Persistence Parity And Worker Store Durability

**Description:** Replace always-in-memory worker persistence with SQL-backed storage where the app uses SQL for durable runtime state, and align worker events with the durable run/event model.

**Affected Areas**

- `backend/src/hello_sales_backend/platform/composition/app_container.py`
- `backend/src/hello_sales_backend/platform/workers/persistence.py`
- `backend/src/hello_sales_backend/platform/workers/memory.py`
- `backend/src/hello_sales_backend/platform/db/models.py`
- `backend/src/hello_sales_backend/platform/db/repositories.py`
- Alembic migrations and worker tests/smokes

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ERR-BG-001 | Important background work is not in-memory-only | Worker run storage | SQL integration tests |
| ERR-DATA-001 | Persistence failures are distinct | Worker repository writes | Negative repository tests where practical |
| TEST-INT-001 | Persistence changes have integration coverage | DB models/repositories | Migration and repository tests |
| OBS-DIAG-001 | Worker state inspectable after process/runtime boundaries | Diagnostics and detail views | Worker diagnostics tests |

**Current-System Analysis**

- Current composition always does `worker_store: WorkerStorePort = InMemoryWorkerStore()`, even when agent and session stores are SQL-backed.
- This violates the operational contract for important background work and makes workers less reliable than agents.
- Worker events are already modeled, so SQL persistence can follow the agent event pattern.

**Options Considered**

- **Option A:** Add `SqlAlchemyWorkerStore` and use it for non-SQLite databases, mirroring agents/sessions.
- **Option B:** Store workers only in the new shared execution tables and remove `WorkerStorePort`.
- **Option C:** Keep in-memory worker store but persist only task snapshots.

**Chosen Approach**

- If the shared envelope migration lands in Sprint 12, use Option B with compatibility ports. If migration is staged, use Option A first to close the durability gap immediately.

**Decision Justification**

- The non-negotiable requirement is persistence parity. Option C does not satisfy ERR-BG-001 because task state alone cannot reconstruct worker input/output/events.
- Option B is cleaner but higher risk. Option A is a valid intermediate step if needed.

**Execution Notes**

- SQLite test mode may continue using in-memory stores only where existing tests explicitly rely on that behavior, but production-like SQL paths must persist workers.
- Worker store migration must include events, output payload, error details, prompt refs, attempt count, timeout, task id, provider/model, and execution mode.

**Expected Evidence**

- **Tests:** worker run survives store reload; worker events list from SQL; app container selects SQL worker store for SQL DB.
- **Runtime Evidence:** worker detail and diagnostics work after execution with SQL store.
- **Review Checks:** no unconditional `InMemoryWorkerStore()` in production composition.

---

### Feature 4: Reconcile Task Ownership With Run Lifecycle

**Description:** Make background tasks infrastructure-owned execution handles that update or reconcile durable run state without becoming a second uncoordinated lifecycle authority.

**Affected Areas**

- `backend/src/hello_sales_backend/platform/tasks/`
- `AgentRunService._schedule_turn()`
- `AgentRunService._recover_orphaned_run()`
- `WorkerRunService.start_run()` and `cancel_run()`
- Runtime failure/cancellation handlers
- Diagnostics and task/run reconciliation tests

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ERR-BG-001 | Background work terminal state inspectable | Task snapshots and run terminal state | Failure tests |
| OBS-BG-001 | Task state visible and reconciled | Diagnostics/recovery paths | Orphan recovery tests |
| WF-STATE-001 | Workflow-backed execution terminal outcomes explicit | Stageflow worker execution | Workflow-mode tests |
| WF-RETRY-001 | Cancellation semantics explicit | Agent/worker cancel flows | Cancellation tests |

**Current-System Analysis**

- Agent execution uses `run_id` as `task_id`; worker execution creates a different `task_id`.
- Agent orphan recovery exists because durable run state and task runner state can drift.
- Worker cancellation depends on `self._tasks.cancel(run.task_id)` but does not itself set terminal cancellation state; runtime/task completion must do that later.

**Options Considered**

- **Option A:** Make task state authoritative and derive run state from task snapshots.
- **Option B:** Make durable run state authoritative and treat task snapshots as execution-handle telemetry.
- **Option C:** Keep both authoritative and add more recovery logic.

**Chosen Approach**

- Adopt Option B. Durable run state is the authoritative lifecycle. Task state is evidence and control surface for in-process execution.

**Decision Justification**

- Option B satisfies LLM-RUN-001 and ERR-BG-001 while preserving operational task metadata.
- Option A cannot represent agent approvals, worker retry attempts, structured validation, or prompt details by itself.
- Option C is the current complexity source.

**Execution Notes**

- Standardize run/task linkage: every durable run may have zero or more task handles, but the current active task should be explicit.
- Reconciliation should produce stable error codes such as `execution.run.orphaned` or mode-specific subcodes.
- Cancellation should produce durable terminal state or a visible pending-cancellation state, not just a best-effort task cancel.

**Expected Evidence**

- **Tests:** agent orphan recovery; worker task missing recovery; cancellation when task exists/missing; workflow-backed terminal failure.
- **Runtime Evidence:** diagnostics can show durable run state and current task snapshot without contradiction.
- **Review Checks:** no new fire-and-forget execution paths.

---

### Feature 5: Backward-Compatible Module Facades And Narrow APIs

**Description:** Preserve existing `/sessions`, `/agent-runs`, and `/worker-runs` behavior while adding internal/generalized execution APIs only where required.

**Affected Areas**

- Entrypoint routes
- Module service facades
- Commands/views
- Smoke suites and docs

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-ENTRY-001 | Routes stay thin | HTTP route files | Route review |
| ARCH-MODULE-001 | Public APIs stable and small | Module exports and views | API/smoke tests |
| LLM-EXPOSE-001 | Runtime exposed through modules | Agent/worker/session routes | Import review |
| PRE-SCOPE-004 | Public surfaces remain narrow | New generic APIs | Docs and route inventory |

**Current-System Analysis**

- Current routes are mostly thin and call module services.
- The larger issue is service coupling: `SessionService` imports `AgentRunService` and exposes agent approval/events through session methods.
- Backward compatibility should be maintained through facade methods while the underlying attachment/execution substrate is generalized.

**Options Considered**

- **Option A:** Replace all routes with a new `/executions` API in Sprint 12.
- **Option B:** Keep existing routes and add a small internal execution facade used by services.
- **Option C:** Do no API work and only change persistence.

**Chosen Approach**

- Adopt Option B. Internals can unify first; public API modernization can follow once behavior is stable.

**Decision Justification**

- Option B avoids broad client breakage and keeps Sprint 12 focused on architecture.
- Option A may be desirable later but expands scope and review risk.
- Option C does not address the conceptual coupling between sessions and runs.

**Execution Notes**

- Existing commands/views can remain while new generic commands/views are added behind module boundaries.
- Any new route must be operationally justified and documented. Do not create speculative product APIs.

**Expected Evidence**

- **Tests:** existing session, agent, and worker route tests/smokes still pass; new facade tests cover generalized flows.
- **Runtime Evidence:** route responses preserve stable ids/status/error fields.
- **Review Checks:** routes do not import platform stores, DB sessions, task runner, or provider adapters directly.

## Deviations

| Requirement ID | Deviation | Reason | Risk | Disposition | Follow-up |
| --- | --- | --- | --- | --- | --- |
| Reasoning protocol tracker input | Tracker is not yet present | User asked to create the Sprint 12 reasoning document first | Execution scope could drift if tracker is written later without aligning to this reasoning | Temporary | Create `ops/sprints/sprint-12-runtime-unification/tracker.md` before implementation and reconcile it with this document. |
| External research step | No external research performed | Sprint is internal architecture refactor governed by local contracts/code | Missing an external pattern is possible but unlikely to change delivery decisions | Permanent for reasoning phase | Revisit only if execution introduces a new external framework, provider, or storage technology. |

## Cross-Cutting Reasoning

### Major Decision Summary

- **Session becomes a durable activity timeline:** Driven by ARCH-SHARED-001, LLM-RUN-001, and PRE-SCOPE-003. This preserves the useful append-only chronology while removing the false assumption that every session is a chat.
- **Shared execution envelope plus mode-specific details:** Driven by LLM-BOUNDARY-001, LLM-TOOL-001, LLM-IO-001, and LLM-RUN-001. Common lifecycle belongs in one place; agent/worker semantics remain explicit.
- **Durable run state is authoritative over task state:** Driven by ERR-BG-001 and OBS-BG-001. Task snapshots are operational evidence and control handles, not the domain source of truth.
- **Worker persistence parity is required:** Driven by ERR-DATA-001 and LLM-RUN-001. Always-in-memory worker runs are not acceptable for important background execution.
- **Backward-compatible facade migration:** Driven by ARCH-MODULE-001 and PRE-SCOPE-004. Internal elegance should not require unnecessary public API churn in the same sprint.

### Trade-offs

- **More migration work now, less runtime ambiguity later:** SQL persistence and shared run envelopes increase Sprint 12 scope, but they directly address the current coordination problems.
- **Keep `Session` name for compatibility:** This is less semantically pure than renaming to `ActivityTimeline`, but it avoids broad API churn.
- **Do not fully erase specialized models:** The result is not a single tiny model, but it is cleaner because shared concerns move to the envelope and specialized concerns stay where they belong.

### Assumptions

- The product brief is still not stable enough to justify product-specific session kinds or workflow types.
- Existing smoke suites are the baseline regression gate.
- Backward compatibility for current API surfaces is preferred unless the user explicitly approves a breaking API migration.
- SQLAlchemy/Alembic remain the persistence path for durable runtime state.

### Dependencies

- Existing agent, worker, session, task, and LLM runtime contracts.
- Existing SQL model and repository patterns.
- Existing smoke harness for agent/session/worker runtime behavior.
- A Sprint 12 tracker still needs to be created and aligned before implementation.

### Evidence Review Checklist

- Review can trace every feature decision back to explicit requirement IDs.
- Review can verify every operational contract file and Python contract module was considered.
- Review can confirm worker runs are no longer production in-memory-only.
- Review can inspect durable run/session/task correlation across agent and worker paths.
- Review can see tests for status mapping, persistence, cancellation, orphan recovery, and backward-compatible smokes.
- Review can identify any remaining compatibility aliases or staged migrations by requirement ID.

## Phase Exit Criteria

- [x] Sprint scope is covered from the user-approved Sprint 12 direction.
- [x] Applicable requirements are mapped.
- [x] Ambiguous and non-applicable requirements are recorded.
- [x] Latest relevant guidance was reviewed through current local contracts; external research was explicitly deemed unnecessary.
- [x] Research/source basis is tied to decisions, risks, alternatives, and evidence expectations.
- [x] Important decisions are explicitly justified.
- [x] Non-trivial alternatives are discussed.
- [x] Deviations, assumptions, risks, and unknowns are documented.
- [x] Expected evidence is defined.
- [ ] Tracker scope is fully covered. Deferred because the tracker does not exist yet.

## Documentation Updates

- `ops/sprints/sprint-12-runtime-unification/tracker.md`: Must be created before execution and aligned with this reasoning.
- `ops/sprints/README.md`: Should add Sprint 12 once the tracker exists.
- Backend runtime docs: Should document the final session/run/task model after implementation.
- Testing and operations docs: Should document the smoke commands and failure evidence expected for unified execution.
