# Sprint Reasoning: Runtime Unification

> Project: HelloSales
> Sprint ID: sprint-12-runtime-unification
> Created: 2026-05-03
> Revised: 2026-05-06
> Output: `ops/sprints/sprint-12-runtime-unification/reasoning.md`

## Overview

**Sprint:** Runtime Unification
**Purpose:** Make LLM/runtime execution durable, inspectable, and extensible without forcing every execution path into a conversational session.
**Tracker:** To be created before execution. This reasoning uses the user-approved Sprint 12 scope: simplify and unify the currently convoluted session/agent/worker execution model in one clean migration.
**Depends On:** `sprint-02-worker-runtime-foundation`, `sprint-04-session-substrate-foundation`, `sprint-09-context-engineering`, `sprint-10-rag-primitives`, `sprint-11-voice-primitives`

Sprint 12 should not generalize `Session` into a universal activity container. That would make a conversation concept carry background agents, sub-agents, workers, and pipeline execution that do not naturally belong to a user-facing thread.

The target abstraction is:

- **Conversation session:** durable user-facing conversational continuity: messages, turns, summaries, approvals, and conversation-scoped attachments.
- **Execution run:** universal durable lifecycle owner for agent turns, background agents, sub-agents, workers, workflow steps, voice runs, and future runtime work.
- **Run event:** ordered operational chronology for one execution run.
- **Task handle:** infrastructure handle for async/background execution, not the authoritative lifecycle.
- **Correlation links:** optional references that connect runs to sessions, parent runs, workflow/job groups, request ids, trace ids, actors, and organizations.
- **Mode details:** agent turns, tool calls, approvals, worker attempts, schemas, structured outputs, and provider metadata remain explicit where their semantics matter.

The core rule is:

> Runs are always first-class. Sessions are optional parents only when the work belongs to a conversation.

## Requirement Map

### Contracts Reviewed For This Sprint

| Contract File | Area | Applicability | Why It Matters |
| --- | --- | --- | --- |
| `ops/operational-contract/architecture.md` | Layering and module boundaries | Applicable | The sprint changes core runtime boundaries, persistence, composition, and public module APIs. |
| `ops/operational-contract/errors.md` | Failure shape and terminal state | Applicable | Runtime unification must not hide orphaned runs, background failures, persistence failures, or cancellation. |
| `ops/operational-contract/observability.md` | Correlation and diagnostics | Applicable | Runs, events, sessions, tasks, workflows, and traces need one inspectable operational story. |
| `ops/operational-contract/testing.md` | Unit, integration, smoke evidence | Applicable | Persistence and lifecycle changes require deterministic tests and runtime smoke coverage. |
| `ops/operational-contract/workflows.md` | Orchestration boundaries | Applicable | Worker direct vs Stageflow execution currently branches at runtime and must remain explicit. |
| `ops/operational-contract/llm.md` | Agent/worker lifecycle and prompt evidence | Applicable | Agent and worker execution are LLM-backed and must keep mode-specific policy visible. |
| `ops/operational-contract/pre-brief-scope.md` | Product-neutral foundation | Applicable | This is foundation work and must not invent product-specific session, job, or workflow concepts. |
| `ops/operational-contract/frontend.md` | Frontend boundaries | Non-Applicable unless frontend is touched | Sprint 12 should be backend/runtime-first; any UI change must use typed feature-owned API seams. |
| Python contract modules under `backend/src/hello_sales_backend/**/contracts.py` | Runtime/provider code contracts | Applicable where touched | Agent, worker, LLM, voice, web search, auth, and smoke contracts define public seams that must remain stable or migrate intentionally. |

### Requirement Index Used In This Sprint

| Requirement ID | Title | Area | Applicability | Why It Matters For This Sprint |
| --- | --- | --- | --- | --- |
| ARCH-CORE-001 | Module boundaries must remain explicit | Architecture | Applicable | Execution substrate must not become a god module that absorbs sessions, agents, workers, and tasks without clear ownership. |
| ARCH-CORE-002 | Dependency direction must point inward | Architecture | Applicable | Use cases must depend on ports and public facades, not concrete SQL/task/runtime internals. |
| ARCH-LAYER-002 | Use cases depend on ports, not infra | Architecture | Applicable | Unified persistence and run orchestration need injectable stores/fakes. |
| ARCH-ENTRY-001 | Transport adapters must stay thin | Architecture | Applicable | Session, agent, and worker routes should remain facade calls only. |
| ARCH-MODULE-001 | Module public APIs must stay small and coherent | Architecture | Applicable | Existing agent/worker/session APIs may change where the current shape preserves the wrong abstraction. |
| ARCH-COMP-001 | Composition must happen through registrars | Architecture | Applicable | App container wiring currently knows too much and always uses `InMemoryWorkerStore`; Sprint 12 must improve this without route-level coupling. |
| ARCH-SHARED-001 | Shared and platform code must stay domain-neutral | Architecture | Applicable | A generic execution substrate belongs in platform only if it remains product-neutral and does not absorb conversation semantics. |
| ERR-CORE-001 | No failure may disappear | Errors | Applicable | Unified lifecycle must preserve terminal failure for orphaned runs, background failures, retries, and persistence errors. |
| ERR-SHAPE-001 | Operational errors must preserve canonical shape | Errors | Applicable | Migration and runtime failures need stable codes/details. |
| ERR-CODE-001 | Error codes must be stable and machine-usable | Errors | Applicable | New execution/session errors need specific codes, not generic `internal`. |
| ERR-TRANS-001 | Error translation must preserve cause and context | Errors | Applicable | Runtime, task, workflow, and store boundary errors must keep cause and ids. |
| ERR-RETRY-001 | Retryable errors must use explicit bounded policy | Errors | Applicable | Worker retry and agent LLM retry must survive unification without hidden retry loops. |
| ERR-BG-001 | Background work must end in explicit inspectable failure state | Errors | Applicable | Task/run drift is a current design pressure point. |
| ERR-DATA-001 | Persistence and data failures must be loud and distinct | Errors | Applicable | Worker runs are currently in-memory only; SQL persistence and migrations must fail loudly. |
| ERR-REDACT-001 | Redaction must protect secrets without destroying diagnosis | Errors | Applicable | Unified events may contain prompt, input, tool, worker, and provider metadata. |
| OBS-CORE-001 | Failures must produce structured operational signals | Observability | Applicable | Unified runs should make failure visible in events, state, and diagnostics. |
| OBS-CORR-001 | Correlation identifiers must survive subsystem boundaries | Observability | Applicable | `request_id`, `trace_id`, `actor_id`, `session_id`, `run_id`, `parent_run_id`, `root_run_id`, `task_id`, and prompt refs must stay connected. |
| OBS-DIAG-001 | Diagnostics surfaces must expose operator-relevant state | Observability | Applicable | Diagnostics should expose active/recent runs, conversation-linked runs, task handles, orphan reconciliation, and recent terminal failures. |
| OBS-BG-001 | Background work must have visible terminal state | Observability | Applicable | Task snapshots and durable run state must reconcile rather than disagree silently. |
| TEST-SEAM-001 | Collaborators must be replaceable through public seams | Testing | Applicable | New stores, orchestrators, and adapters need fakeable ports. |
| TEST-UNIT-001 | Business logic must have unit coverage | Testing | Applicable | Status mapping, event mapping, correlation policy, and attachment policy are deterministic logic. |
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
| PRE-SCOPE-003 | Favor operational scaffolding over assumptions | Pre-Brief | Applicable | The sprint should improve seams, durability, correlation, and observability. |
| PRE-SCOPE-004 | Public APIs remain narrow | Pre-Brief | Applicable | Replace confused public surfaces with narrow coherent ones; do not keep compatibility layers that preserve bad concepts. |
| FE-* | Frontend requirements | Frontend | Non-Applicable unless frontend changes | No frontend implementation is required for the runtime unification sprint. |

### Applicable Requirements

- **ARCH-CORE-001 / ARCH-MODULE-001:** The new execution substrate must have a small, explicit public API. It should not become a generic dumping ground for conversation, worker, task, and workflow behavior.
- **ARCH-LAYER-002 / TEST-SEAM-001:** Use cases should depend on narrow store/orchestrator ports. Agent and worker tests must replace stores and runtimes without private patching.
- **ARCH-COMP-001 / ERR-DATA-001:** Composition must stop wiring workers to `InMemoryWorkerStore()` for all database configurations. Worker run durability must match agent durability.
- **ERR-BG-001 / OBS-BG-001 / LLM-RUN-001:** Background task state and durable run state must reconcile explicitly. The current orphan recovery logic is a symptom to design around.
- **LLM-BOUNDARY-001 / LLM-TOOL-001 / LLM-IO-001:** Unification should share identity, persistence, lifecycle, correlation, and events, but keep agent turns/tool calls and worker schemas/attempts mode-specific.
- **OBS-CORR-001 / LLM-PROMPT-001:** Unified run records must retain request, trace, actor, optional session, optional parent run, optional workflow/job group, task, and effective prompt references.
- **PRE-SCOPE-002 / PRE-SCOPE-004:** Do not create product-specific session kinds, workflow types, or job models. Keep new public surfaces minimal and coherent.

### Non-Applicable Requirements

- **FE-STRUCT-001 through FE-EXT-001:** Not applicable unless Sprint 12 adds frontend surfaces. If a UI is later added, it must be feature-owned with typed API access.
- **Provider-specific parts of ERR-PROVIDER-001:** No new external provider integration is planned. Existing LLM provider failure classification still applies to agent/worker execution.
- **Voice-specific Python contracts:** `platform/voice/contracts.py` was reviewed; Sprint 12 should not change voice provider semantics unless voice runs are later attached to the unified execution substrate.
- **Auth provider contract:** Reviewed and not directly changed. Auth context propagation remains relevant through existing `AuthContext` fields.

### Ambiguous Or Conflicting Requirements

- **Session as conversation vs generic timeline:** The previous plan generalized session into a durable activity timeline. That is rejected here. Session should remain conversation-oriented; non-conversational work should use runs and correlation links without requiring a session.
- **Conversation lifecycle vs run lifecycle:** Current code marks sessions `COMPLETED`, `FAILED`, or `CANCELLED` based on attached agent execution. A conversation may contain multiple runs, so session status cannot blindly mirror one latest run.
- **Run lifecycle vs runtime behavior:** Every execution needs the same durable lifecycle, correlation, and event spine, but agents and workers do different work. The clean split is one `ExecutionRun` for lifecycle/correlation plus owned runtime records for the behavior that is actually specific: agent turns/tool calls/approvals, worker attempts/schemas/outputs, and future mode-specific facts.
- **Task identity mapping:** Agent turns currently use `task_id=run.run_id`; workers generate a separate task id and store it on `WorkerRun`. A unified model should support explicit task handles linked to a run instead of assuming run id and task id are the same.
- **Workflow/job grouping:** Pipeline-style non-conversational work may eventually need a workflow or job grouping model. Sprint 12 should allow optional `workflow_id` or `job_id` correlation, but should not invent a product-specific grouping model before the brief.
- **Breaking cleanup vs current clients:** Existing routes and smokes likely depend on `/sessions`, `/agent-runs`, and `/worker-runs` shapes. Sprint 12 should prefer the clean model over preserving confusing API shapes.

### Open Questions

- What is the final route/API shape for conversation sessions, execution runs, and runtime-specific operations after the breaking cleanup?
- Should workflow/job correlation be a nullable string field on `ExecutionRun` for now, or deferred entirely until a concrete orchestration use case exists?

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

- **Use session as the universal execution container:** Rejected because sessions are naturally conversational and forcing background workers/sub-agents/pipelines into sessions weakens the model.
- **Use an external workflow engine as the universal execution model:** Rejected because WF-SCOPE-001 says workflows are for real orchestration, not ordinary business logic.
- **Collapse agents and workers into one runtime class:** Rejected because LLM-BOUNDARY-001 requires conversational and structured policy to remain separated where semantics differ.
- **Leave worker runs in memory and only document the caveat:** Rejected because ERR-BG-001 and ERR-DATA-001 forbid in-memory-only tracking for important background work.

### Impact On Reasoning

- The design should introduce a shared execution run and event model while preserving focused agent/worker-owned behavior tables and services.
- Session should remain conversation-specific and optional for execution runs.
- Non-conversational work should be correlated through `run_id`, `parent_run_id`, `root_run_id`, `workflow_id` or `job_id` where applicable, `request_id`, and `trace_id`, not by creating implicit sessions.
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

### Feature 1: Keep Session Conversational And Optional

**Description:** Preserve `ConversationSession` as the user-facing conversation/thread concept, while decoupling conversation creation, status, and storage from mandatory agent execution.

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
| ARCH-SHARED-001 | Session substrate stays product-neutral but not universal | Session model and item taxonomy | Naming/import review |
| LLM-RUN-001 | Conversation-linked LLM runs remain inspectable | Optional session/run links | Session + run integration tests |
| OBS-CORR-001 | Session/run/task ids remain correlated | Session id on execution runs and events | Detail view assertions |
| PRE-SCOPE-002 | No product-specific session kinds | Session API and item taxonomy | Review checklist |

**Current-System Analysis**

- The session model already has append-only `SessionItem` records with `run_id`, `turn_id`, `tool_call_id`, and prompt metadata. That is useful for conversation chronology.
- The restrictive part is service behavior. `SessionService.create_session()` immediately creates an agent run, so session existence implies agent execution.
- `SessionStatus` currently mirrors attached agent state. That does not generalize even within conversations, because one conversation can contain multiple turns/runs or pending background work.

**Options Considered**

- **Option A:** Generalize `Session` into a durable activity timeline for every runtime use case.
- **Option B:** Keep the `Session` name but change the API/docs so it only means conversation session.
- **Option C:** Rename `Session` to `ConversationSession` or `Conversation` as part of the breaking cleanup.

**Chosen Approach**

- Adopt Option C for public/domain naming: use `ConversationSession` or `Conversation` for conversation storage and `ExecutionRun` for execution storage. Persistence internals may keep an old table name only if the public model, services, and migrations make the meaning unambiguous.

**Decision Justification**

- Option C is the clearest model and matches the desired one-sweep cleanup.
- Option B is less clean because it keeps an overloaded word in circulation, but it is still better than turning sessions into generic timelines. It must not preserve implicit sessions or session-owned execution lifecycle.
- Option A would preserve the current conceptual confusion under a more generic name.

**Execution Notes**

- Conversation creation must not create an agent run.
- Message append may create a linked `ExecutionRun` when the operation asks an agent to respond, but the run lifecycle belongs to `ExecutionRun`.
- Session/conversation status should represent conversation state, not mirror the latest attached run.
- Remove `latest_run_id`; conversation-linked runs should be queried by `session_id`/conversation id and ordered by execution timestamps/events.

**Expected Evidence**

- **Tests:** creating a conversation without an agent run; creating a conversation-linked execution run; appending messages without making conversation storage the lifecycle authority.
- **Runtime Evidence:** conversation detail shows conversation chronology with stable run references.
- **Review Checks:** no code path creates a session solely because a worker/background agent needs execution tracking.

---

### Feature 2: Introduce ExecutionRun As The Lifecycle Root

**Description:** Add `ExecutionRun` as the durable lifecycle root for every runtime execution. Replace `AgentRun` and `WorkerRun` as lifecycle-owner tables in the same migration. Runtime-specific records remain only for behavior that is genuinely specific to agents, workers, voice, workflows, or future modes.

**Affected Areas**

- New or revised platform execution models/contracts
- Agent and worker run models/stores/views
- SQL models and migrations
- Runtime diagnostics and events
- Existing `AgentRunService` and `WorkerRunService`

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| LLM-RUN-001 | Runs/events durable or inspectable | `ExecutionRun` lifecycle root | Persistence and event tests |
| LLM-BOUNDARY-001 | Mode policy remains separate | Agent turns and worker attempts | Unit tests per mode |
| LLM-TOOL-001 | Agent tools remain explicit | Agent tool call detail records | Approval/tool regression tests |
| LLM-IO-001 | Worker schemas remain explicit | Worker input/output validation | Worker runtime tests |
| OBS-CORR-001 | Correlation metadata persists | Run/task/session/parent/workflow fields | Detail view assertions |

**Current-System Analysis**

- `AgentRun` and `WorkerRun` duplicate identity, status, prompt, timing, actor, request, trace, error, and event concepts.
- Their differences are real: agents have turns/tool calls/approvals; workers have structured input/output, attempts, timeouts, provider/model output, and direct vs Stageflow execution.
- `ExecutionRun` should own the common lifecycle and correlation fields. Agent and worker tables should only own the facts that are specific to how that runtime behaves.

**Options Considered**

- **Option A:** Replace `AgentRun` and `WorkerRun` with one large `ExecutionRun` containing every possible field.
- **Option B:** Make `ExecutionRun` the lifecycle root and move only behavior-specific facts into focused runtime-owned tables.
- **Option C:** Keep existing tables and only add adapter functions that map both into a common view.

**Chosen Approach**

- Adopt Option B in one migration. Replace the current lifecycle tables with `execution_runs` plus focused runtime-owned tables. Do not add adapter-only views as a half measure.

**Decision Justification**

- Option B best satisfies LLM-RUN-001 and LLM-BOUNDARY-001 together: one lifecycle root, separate runtime behavior.
- Option A becomes a sparse god record and weakens mode boundaries.
- Option C improves views but leaves duplicated persistence and lifecycle ownership unresolved.

**Execution Notes**

- Define a small shared status enum only for common lifecycle: pending, running, awaiting_input_or_approval, retrying, completed, failed, cancelled, timed_out.
- Add correlation fields deliberately: `session_id` nullable, `parent_run_id` nullable, `root_run_id` nullable, `workflow_id` or `job_id` nullable if needed, `request_id`, `trace_id`, `actor_id`, `org_id`.
- Map agent and worker statuses intentionally. Do not make lossy mappings where semantics differ.
- Preserve prompt references on `ExecutionRun` or a normalized prompt snapshot table.
- Do not create an `ExecutionRun` API that exposes mode-specific internals through a generic payload blob.
- `AgentRun` and `WorkerRun` should cease to exist as lifecycle tables after Sprint 12. If their names survive at all, they should refer only to focused behavior records, and renaming them is preferable.

**Expected Evidence**

- **Tests:** status mapping; agent run creation; worker run creation; prompt ref propagation; parent/root run propagation; terminal error propagation.
- **Runtime Evidence:** diagnostics can list active/recent runs across agent and worker modes, with optional session links.
- **Review Checks:** no mode-specific tool/schema policy in shared envelope code.

---

### Feature 3: Add Run Events As The Canonical Execution Chronology

**Description:** Store ordered execution events against `ExecutionRun` so background agents, sub-agents, workers, and conversation-linked agent turns have a shared operational event stream.

**Affected Areas**

- New or revised platform execution event models/contracts
- Agent stream event persistence
- Worker run event persistence
- SQL models and migrations
- Diagnostics and event routes/views

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| LLM-RUN-001 | Runs/events durable or inspectable | Execution run events | Event persistence tests |
| OBS-CORE-001 | Failures produce structured signals | Terminal/failure events | Negative tests |
| OBS-CORR-001 | Correlation survives subsystem boundaries | Event metadata | Detail view assertions |
| ERR-REDACT-001 | Events do not leak secrets | Event payload policy | Payload review/tests where practical |

**Current-System Analysis**

- Agent events and worker events are already modeled separately.
- Session item chronology is useful for conversation rendering, but it should not be the canonical event stream for non-conversational work.
- A shared event stream gives diagnostics one operational story without making sessions mandatory.

**Options Considered**

- **Option A:** Continue using agent events, worker events, and session items as separate chronologies.
- **Option B:** Add shared `ExecutionRunEvent` as the canonical event store and rebuild runtime-specific views from it where useful.
- **Option C:** Store all events only as session items.

**Chosen Approach**

- Adopt Option B.

**Decision Justification**

- Option B centralizes operational chronology and lets public behavior be rebuilt around the clean execution model.
- Option A leaves duplicated diagnostics and inconsistent event retention.
- Option C incorrectly makes sessions mandatory for all runtime events.

**Execution Notes**

- Event sequence should be scoped to `run_id`.
- Event payloads should be structured and redacted according to existing operational contracts.
- Conversation sessions can project relevant run events into session items or views where needed, but that projection is not the source of truth.

**Expected Evidence**

- **Tests:** event ordering; agent event projection; worker event projection; failure event shape.
- **Runtime Evidence:** run detail can show ordered events for conversational and non-conversational runs.
- **Review Checks:** no worker/background event path requires a `session_id`.

---

### Feature 4: Persistence Parity And Worker Store Durability

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
- Worker events are already modeled, so SQL persistence can follow the agent event pattern or the new execution event pattern.

**Options Considered**

- **Option A:** Add `SqlAlchemyWorkerStore` and use it for non-SQLite databases, mirroring agents/sessions.
- **Option B:** Store workers through `execution_runs`, `execution_run_events`, and focused worker-owned tables.
- **Option C:** Keep in-memory worker store but persist only task snapshots.

**Chosen Approach**

- Adopt Option B in the Sprint 12 migration. Do not add a temporary SQL worker store as a stopping point.

**Decision Justification**

- The non-negotiable requirement is persistence parity. Option C does not satisfy ERR-BG-001 because task state alone cannot reconstruct worker input/output/events.
- Option B is cleaner and matches the one-sweep migration goal. Option A is a half measure because it persists workers while leaving lifecycle duplication intact.

**Execution Notes**

- SQLite tests should use the same durable execution model unless a unit test is explicitly testing an in-memory fake behind a port.
- Worker store migration must include events, output payload, error details, prompt refs, attempt count, timeout, task id, provider/model, and execution mode.

**Expected Evidence**

- **Tests:** worker run survives store reload; worker events list from SQL; app container selects SQL worker store for SQL DB.
- **Runtime Evidence:** worker detail and diagnostics work after execution with SQL store.
- **Review Checks:** no unconditional `InMemoryWorkerStore()` in production composition.

---

### Feature 5: Reconcile Task Ownership With Run Lifecycle

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
- Option A cannot represent agent approvals, worker retry attempts, structured validation, prompt details, parentage, or prompt refs by itself.
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

### Feature 6: Clean Module APIs In One Sweep

**Description:** Replace confused session/agent/worker API boundaries with narrow final module APIs that match the new model. Do not keep compatibility routes or facades solely to preserve the old abstraction.

**Affected Areas**

- Entrypoint routes
- Module services
- Commands/views
- Smoke suites and docs

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-ENTRY-001 | Routes stay thin | HTTP route files | Route review |
| ARCH-MODULE-001 | Public APIs coherent and small | Module exports and views | API/smoke tests |
| LLM-EXPOSE-001 | Runtime exposed through modules | Agent/worker/session routes | Import review |
| PRE-SCOPE-004 | Public surfaces remain narrow | New generic APIs | Docs and route inventory |

**Current-System Analysis**

- Current routes are mostly thin and call module services.
- The larger issue is service coupling: `SessionService` imports `AgentRunService` and exposes agent approval/events through session methods.
- The route/module shape should be cleaned so conversation APIs expose conversation behavior, execution APIs expose lifecycle/events/cancellation, and runtime-specific APIs expose behavior-specific operations only.

**Options Considered**

- **Option A:** Replace the current route/module shape with final conversation, execution, and runtime-specific APIs in Sprint 12.
- **Option B:** Keep existing routes and add an internal execution facade used by services.
- **Option C:** Do no API work and only change persistence.

**Chosen Approach**

- Adopt Option A. This sprint is a breaking cleanup, so route and module APIs should move to the clean model now.

**Decision Justification**

- Option A prevents the old session-owned execution model from surviving behind compatibility surfaces.
- Option B is a half measure: it improves internals while preserving the confusing external model.
- Option C does not address the conceptual coupling between sessions and runs.

**Execution Notes**

- Remove or rename commands/views that encode session-owned execution.
- Any new route must be operationally justified and documented. Do not create speculative product APIs.
- Conversation routes should expose conversation behavior. Execution routes should expose common lifecycle/events/cancellation. Worker/agent routes should expose behavior-specific operations only.
- The execution API should expose only generic lifecycle operations: create when appropriate, read detail, list/query, list events, and cancel.
- Agent-specific operations such as turn inspection, tool calls, approvals, and artifacts should remain under agent-owned APIs.
- Worker-specific operations such as attempts, structured input/output, and worker-owned result surfaces should remain under worker-owned APIs.

**Expected Evidence**

- **Tests:** old session-owned execution assumptions are removed or rewritten; new route tests cover conversation, execution lifecycle/events, worker runs, and agent behavior.
- **Runtime Evidence:** route responses expose the final ids/status/error fields from the clean model.
- **Review Checks:** routes do not import platform stores, DB sessions, task runner, or provider adapters directly.

## Deviations

| Requirement ID | Deviation | Reason | Risk | Disposition | Follow-up |
| --- | --- | --- | --- | --- | --- |
| Reasoning protocol tracker input | Tracker is not yet present | User asked to create the Sprint 12 reasoning document first | Execution scope could drift if tracker is written later without aligning to this reasoning | Temporary | Create `ops/sprints/sprint-12-runtime-unification/tracker.md` before implementation and reconcile it with this document. |
| External research step | No external research performed | Sprint is internal architecture refactor governed by local contracts/code | Missing an external pattern is possible but unlikely to change delivery decisions | Permanent for reasoning phase | Revisit only if execution introduces a new external framework, provider, or storage technology. |
| Prior session-generalization plan | The previous plan treated session as a durable activity timeline | User raised a valid architectural concern that sessions should track conversations, not all runtime work | If not corrected, the sprint could cement a confusing abstraction | Resolved in this revision | Tracker and implementation must use execution runs as the universal primitive and keep sessions optional/conversational. |

## Cross-Cutting Reasoning

### Major Decision Summary

- **Session remains conversational:** Driven by clarity and ARCH-SHARED-001. A session is for user-facing conversational continuity, not every background or pipeline execution.
- **ExecutionRun becomes the universal primitive:** Driven by LLM-RUN-001, ERR-BG-001, OBS-BG-001, and OBS-CORR-001. Every meaningful LLM/runtime execution should have durable lifecycle state independent of session.
- **Run events become the canonical operational chronology:** Driven by OBS-CORE-001 and LLM-RUN-001. Session items are conversation chronology; run events are execution chronology.
- **ExecutionRun plus runtime-owned behavior tables:** Driven by LLM-BOUNDARY-001, LLM-TOOL-001, LLM-IO-001, and LLM-RUN-001. Common lifecycle belongs in one place; agent/worker behavior remains explicit in focused tables/services.
- **Replace `AgentRun` and `WorkerRun` as lifecycle tables:** The old split duplicates lifecycle ownership and should be removed in the same migration.
- **Durable run state is authoritative over task state:** Driven by ERR-BG-001 and OBS-BG-001. Task snapshots are operational evidence and control handles, not the domain source of truth.
- **Worker persistence parity is required:** Driven by ERR-DATA-001 and LLM-RUN-001. Always-in-memory worker runs are not acceptable for important background execution.
- **Breaking API cleanup:** Driven by ARCH-MODULE-001 and PRE-SCOPE-004. This sprint should remove confused public shapes rather than preserving them through compatibility layers.
- **Remove `latest_run_id`:** Conversation state should not cache a single "latest run" pointer as domain truth.
- **Keep the execution API generic:** Lifecycle, events, and cancellation belong to `execution-runs`; agent/worker-specific behavior stays in agent/worker modules.

### Target Relationship Model

```text
ConversationSession 0..1 -> many ExecutionRuns
WorkflowOrJobGroup   0..1 -> many ExecutionRuns
ExecutionRun         0..1 -> many child ExecutionRuns
ExecutionRun         1    -> many RunEvents
ExecutionRun         0    -> many TaskHandles
ExecutionRun         1    -> 0..many runtime-owned behavior records
```

Examples:

- Conversational agent turn: `session_id` present, `run_id` present.
- Sub-agent spawned from chat: `session_id` may be inherited for correlation, `parent_run_id` and `root_run_id` are set, lifecycle is owned by the child `run_id`.
- Background worker triggered by a pipeline: no `session_id`; use `workflow_id` or `job_id` if a grouping exists.
- Background agent triggered by a user action outside chat: no session unless there is an actual user-visible thread.
- Synchronous LLM extraction/classification: create an `ExecutionRun` if durability/diagnostics are required; no session and possibly no task handle.

### Trade-offs

- **More migration work now, less runtime ambiguity later:** SQL persistence, execution runs, and API cleanup increase Sprint 12 scope, but they directly address the current coordination problems.
- **Rename where it clarifies:** `Session` should become `ConversationSession` or `Conversation` if implementation confirms the rename can be completed coherently in the sprint.
- **Do not fully erase specialized models:** The result is not a single tiny model, but it is cleaner because shared lifecycle moves to `ExecutionRun` and specialized behavior stays where it belongs.
- **Do not model full workflow/job grouping yet:** Nullable correlation fields are enough until a concrete orchestration use case justifies a first-class grouping model.
- **Query latest linked runs instead of caching one pointer:** This adds some read complexity, but it removes stale denormalized state and keeps conversation storage from owning execution lifecycle.

### Assumptions

- The product brief is still not stable enough to justify product-specific session kinds, jobs, or workflow types.
- Smoke suites must be rewritten around the new route/API shape where old assumptions encode session-owned execution.
- Sprint 12 is approved as a breaking cleanup; compatibility layers should not be added unless they are temporary test scaffolding inside the same migration.
- SQLAlchemy/Alembic remain the persistence path for durable runtime state.
- Public/domain naming should distinguish conversation storage from execution storage. `Session` may remain only as a shorthand inside conversation-specific text, not as a generic runtime concept.

### Dependencies

- Existing agent, worker, session, task, and LLM runtime contracts.
- Existing SQL model and repository patterns.
- Existing smoke harness for agent/session/worker runtime behavior.
- Sprint 12 tracker scope is captured in `ops/sprints/sprint-12-runtime-unification/tracker.md`.

### Evidence Review Checklist

- Review can trace every feature decision back to explicit requirement IDs.
- Review can verify every operational contract file and Python contract module was considered.
- Review can confirm sessions are no longer required for non-conversational workers/background agents.
- Review can confirm worker runs are no longer production in-memory-only.
- Review can inspect durable run/session/task/parent correlation across agent and worker paths.
- Review can see tests for status mapping, event ordering, parent/root propagation, persistence, cancellation, orphan recovery, and the new route/API shape.
- Review can confirm there are no compatibility aliases, staged migrations, or adapter-only half measures left in the final design.

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
- [x] Tracker scope is fully covered.

## Documentation Updates

- `ops/sprints/sprint-12-runtime-unification/tracker.md`: Created and aligned with this reasoning.
- `ops/sprints/README.md`: Should add Sprint 12 once the tracker exists.
- Backend runtime docs: Should document the final session/run/task model after implementation.
- Testing and operations docs: Should document the smoke commands and failure evidence expected for unified execution.
