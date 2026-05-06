# Sprint Tracker: Runtime Unification

> Project: HelloSales
> Sprint ID: sprint-12-runtime-unification
> Created: 2026-05-06
> Reasoning: `ops/sprints/sprint-12-runtime-unification/reasoning.md`

## Sprint Overview

- **Sprint Name:** Runtime Unification
- **Sprint Focus:** Replace the session-owned agent/worker lifecycle split with a clean execution-run runtime model in one breaking migration.
- **Depends On:** `sprint-02-worker-runtime-foundation`, `sprint-04-session-substrate-foundation`, `sprint-09-context-engineering`, `sprint-10-rag-primitives`, `sprint-11-voice-primitives`
- **Status:** Not Started

## Sprint Goals

- **Primary Goal:** Make `ExecutionRun` the durable lifecycle root for every agent, worker, background agent, sub-agent, workflow step, and future LLM/runtime execution.
- **Secondary Goals:**
  - Keep conversation/session storage conversation-specific and remove session-owned execution lifecycle.
  - Replace `AgentRun` and `WorkerRun` lifecycle tables with `execution_runs`, `execution_run_events`, and focused runtime-owned behavior tables.
  - Make retries, timeouts, cancellation, task handles, provider metadata, prompt refs, parent/root lineage, and Stageflow correlation inspectable through the unified runtime model.
  - Replace confused public/module APIs with final conversation, execution, agent, and worker boundaries. No backwards compatibility layers or adapter-only half measures.

## Execution Checklist

- [ ] **Task 1: Define Final Runtime Contracts**
  > *Description: Establish the clean domain model and public service contracts before touching persistence or routes.*
  - [ ] **Sub-task 1.1:** Add platform execution models for `ExecutionRun`, `ExecutionRunEvent`, shared lifecycle status, run kind, correlation fields, terminal errors, prompt refs, timeout policy, and retry policy/state.
  - [ ] **Sub-task 1.2:** Define runtime-owned behavior records for agent and worker execution without duplicating lifecycle fields.
  - [ ] **Sub-task 1.3:** Rename or re-scope conversation/session models so public/domain naming distinguishes conversation storage from execution storage.
  - [ ] **Sub-task 1.4:** Remove `latest_run_id` from the conversation/session model and replace it with explicit queries over conversation-linked execution runs.
  - [ ] **Sub-task 1.5:** Define status mapping rules from existing agent/worker states into the final shared lifecycle vocabulary.

- [ ] **Task 2: Build SQL Persistence In One Migration**
  > *Description: Replace lifecycle persistence with durable execution tables and remove production dependence on in-memory worker state.*
  - [ ] **Sub-task 2.1:** Add Alembic migration for `execution_runs`, `execution_run_events`, task handle linkage if needed, and runtime-owned agent/worker behavior tables.
  - [ ] **Sub-task 2.2:** Remove `AgentRun` and `WorkerRun` as lifecycle-owner tables from SQL models/repositories.
  - [ ] **Sub-task 2.3:** Persist worker input, output, attempts, timeout state, retry state, provider/model metadata, prompt refs, task ids, execution mode, and terminal errors through the final model.
  - [ ] **Sub-task 2.4:** Persist agent turns, tool calls, approvals, artifacts, prompt refs, provider/model metadata, and terminal errors through the final model.
  - [ ] **Sub-task 2.5:** Update app composition so SQL-backed runtime state never unconditionally uses `InMemoryWorkerStore`.

- [ ] **Task 3: Refactor Agent And Worker Services**
  > *Description: Move lifecycle ownership into execution services while keeping agent and worker behavior explicit.*
  - [ ] **Sub-task 3.1:** Introduce an execution service/store that creates, updates, queries, cancels, and records events for `ExecutionRun`.
  - [ ] **Sub-task 3.2:** Refactor agent services so conversation-linked and background agent work create `ExecutionRun` records and write agent-specific behavior records only for turns/tools/approvals/artifacts.
  - [ ] **Sub-task 3.3:** Refactor worker services so every worker execution creates an `ExecutionRun`, records attempts/output through worker-owned records, and no longer owns lifecycle in `WorkerRun`.
  - [ ] **Sub-task 3.4:** Preserve prompt version propagation from existing agent and worker prompt contracts into `ExecutionRun` and behavior records.
  - [ ] **Sub-task 3.5:** Make provider failures normalize into durable run errors and events without giving provider adapters lifecycle ownership.

- [ ] **Task 4: Reconcile Tasks, Retries, Timeouts, And Cancellation**
  > *Description: Make durable run state authoritative while treating task handles and providers as execution machinery.*
  - [ ] **Sub-task 4.1:** Standardize run-to-task linkage so one run may have zero or more task handles and one current active task where applicable.
  - [ ] **Sub-task 4.2:** Implement cancellation through `ExecutionRun`: request cancellation, cancel active task/provider/tool work where possible, append events, and persist terminal state.
  - [ ] **Sub-task 4.3:** Implement bounded retry policy/state at the execution/runtime layer, with worker attempts recorded explicitly and agent retries constrained around side-effect safety.
  - [ ] **Sub-task 4.4:** Implement timeout policy/state for provider calls, tools, whole runs, and workflow steps without conflating those scopes.
  - [ ] **Sub-task 4.5:** Replace orphan recovery with execution-run reconciliation that produces stable error codes and visible terminal events.

- [ ] **Task 5: Integrate Stageflow As Orchestration Above Runs**
  > *Description: Keep Stageflow responsible for ordering and branching while `ExecutionRun` remains the source of runtime truth.*
  - [ ] **Sub-task 5.1:** Represent Stageflow workflow/step correlation on `ExecutionRun` with `workflow_id`, step key, `root_run_id`, and `parent_run_id` where applicable.
  - [ ] **Sub-task 5.2:** Ensure each meaningful Stageflow step that performs agent/worker work creates or drives a child `ExecutionRun`.
  - [ ] **Sub-task 5.3:** Keep Stageflow retry/timeout/cancellation semantics distinct from run-level retry/timeout/cancellation state.
  - [ ] **Sub-task 5.4:** Make Stageflow consume durable run outcomes to decide next workflow steps, retries, compensation, or terminal workflow failure.
  - [ ] **Sub-task 5.5:** Verify direct worker execution and Stageflow-backed worker execution produce the same inspectable run/event shape.

- [ ] **Task 6: Replace Public And Module APIs**
  > *Description: Move routes and commands to the final model without backwards compatibility routes or old session-owned execution shapes.*
  - [ ] **Sub-task 6.1:** Replace session-owned execution endpoints with conversation routes that expose conversation behavior only.
  - [ ] **Sub-task 6.2:** Add or revise execution routes for generic lifecycle operations: create where appropriate, read detail, list/query, list events, and cancel.
  - [ ] **Sub-task 6.3:** Keep agent-specific operations under agent-owned APIs: turns, tool calls, approvals, artifacts, and agent behavior views.
  - [ ] **Sub-task 6.4:** Keep worker-specific operations under worker-owned APIs: attempts, structured input/output, worker result views, and worker behavior diagnostics.
  - [ ] **Sub-task 6.5:** Update commands/views/schemas so old `AgentRun`, `WorkerRun`, and `latest_run_id` response assumptions are removed.

- [ ] **Task 7: Diagnostics, Observability, And Error Shape**
  > *Description: Make active/recent execution, failures, lineage, prompt refs, task handles, and events easy to inspect.*
  - [ ] **Sub-task 7.1:** Add diagnostics queries for active/recent runs across agent, worker, background agent, sub-agent, and Stageflow-backed modes.
  - [ ] **Sub-task 7.2:** Expose parent/root lineage, optional conversation id, optional workflow id, current task handle, prompt ref, provider/model metadata, retry state, timeout state, and terminal errors.
  - [ ] **Sub-task 7.3:** Ensure failure events use stable codes and preserve cause/context while redacting secrets.
  - [ ] **Sub-task 7.4:** Align observability spans/metrics/logs with `run_id`, `root_run_id`, `parent_run_id`, `conversation_id`, `workflow_id`, `request_id`, and `trace_id`.

## Testing And Documentation Checklist

- [ ] **Unit Tests:** status mapping, correlation policy, event ordering, retry policy, timeout policy, cancellation transitions, and conversation-linked run queries.
- [ ] **Integration Tests:** SQL migrations/repositories, execution service, agent path, worker path, Stageflow-backed worker path, cancellation, orphan reconciliation, and route/API behavior.
- [ ] **Smoke Tests:** rewrite existing session/agent/worker smokes around the final conversation/execution/agent/worker route shape.
- [ ] **Real Provider Smoke:** run at least one provider-backed agent or worker smoke after the runtime migration, or record an explicit justified deferral if provider access is unavailable.
- [ ] **Documentation Updates:** update backend runtime docs, worker runtime docs, agent runtime docs, testing/operations docs, and `ops/sprints/README.md`.

## Risks And Blockers

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| Breaking API migration touches many route tests and smoke suites | High | Sequence API changes after domain/persistence contracts are stable; rewrite tests around final route shape rather than preserving old responses | Open |
| ExecutionRun can become a god object | High | Keep `ExecutionRun` limited to lifecycle, correlation, control, timing, prompt refs, and error state; keep behavior in runtime-owned records | Open |
| Stageflow retry/timeout semantics can blur with run-level retry/timeout semantics | Medium | Store workflow/step correlation separately and document retry/timeout ownership per layer | Open |
| Worker persistence migration can lose attempt/output/error detail | High | Add repository round-trip tests for attempts, outputs, errors, provider/model metadata, prompt refs, and events | Open |
| Cancellation can report success before underlying work stops | Medium | Persist cancellation requested and final terminal state separately; append events for each transition | Open |

## Success Criteria

- [ ] **ExecutionRun is the single lifecycle root:** agent, worker, background agent, sub-agent, direct worker, and Stageflow-backed worker paths all create durable execution runs.
- [ ] **No lifecycle-owned AgentRun or WorkerRun remains:** old lifecycle tables, models, stores, routes, and response assumptions are removed or renamed into focused behavior concepts.
- [ ] **Conversation storage is conversation-only:** conversation creation does not create an agent run, non-conversational work does not create implicit sessions, and `latest_run_id` is gone.
- [ ] **Run events are canonical:** ordered execution events exist for agent, worker, failure, retry, timeout, cancellation, and Stageflow-backed paths.
- [ ] **Tasks are not lifecycle truth:** task handles reconcile with durable run state and orphan/cancellation paths produce visible terminal run state.
- [ ] **Retries/timeouts are explicit:** provider-call, tool, run, and Stageflow step scopes are bounded, inspectable, and not conflated.
- [ ] **Execution API is narrow:** generic lifecycle/events/cancel operations live under execution APIs; agent/worker behavior remains under agent/worker APIs.
- [ ] **Evidence is complete:** unit, integration, smoke, and documentation evidence is recorded below.

## Review And Sign-Off

- Sprint Status: Not Started
- Completion Date: TBD

## Execution Evidence

- Tracker created from `ops/process/execute/tracker-template.md` and aligned with `ops/sprints/sprint-12-runtime-unification/reasoning.md`.
- Execution evidence to be recorded as implementation progresses.
