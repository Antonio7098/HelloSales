# Sprint Tracker: Session Substrate Foundation

> Project: HelloSales
> Sprint ID: sprint-04-session-substrate-foundation
> Created: 2026-04-19

## Sprint Overview

- **Sprint Name:** Session Substrate Foundation
- **Sprint Focus:** Introduce a first-class session substrate and move the public conversational API surface to a session-first model.
- **Depends On:** `ops/sprints/done/sprint-01-observability-foundation/tracker.md`, `ops/sprints/done/sprint-02-worker-runtime-foundation/tracker.md`
- **Status:** Complete

## Sprint Goals

- **Primary Goal:** Replace agent-run-owned conversation state with a neutral session substrate that owns chronology, summaries, and trusted user/org context references.
- **Secondary Goals:**
  - Make `/sessions` the public conversational API root instead of `/agent-runs`.
  - Add configurable X-turn session summarization as background-owned work with explicit lifecycle state.
  - Preserve current conversational execution by adapting the existing agent runtime to attach to sessions rather than own the conversation root.

## Execution Checklist

- [x] **Task 1: Formalize Sprint 4 artifacts and branch setup**
  > *Description: Prepare sprint artifacts and execution context before implementation begins.*
  - [x] **Sub-task 1.1:** Finalize `reasoning.md` and `tracker.md` under `ops/sprints/sprint-04-session-substrate-foundation/`.
  - [x] **Sub-task 1.2:** Start work from `sprint/sprint-04-session-substrate-foundation`.

- [x] **Task 2: Add the session substrate**
  > *Description: Introduce neutral session models, ports, stores, and module-owned services.*
  - [x] **Sub-task 2.1:** Add `platform/sessions/` models and persistence contracts for sessions, session items, session summaries, and trusted user/org context references.
  - [x] **Sub-task 2.2:** Add in-memory and SQL-backed session persistence plus the required migration(s).
  - [x] **Sub-task 2.3:** Add `modules/sessions/` bootstrap, commands, views, and service/facade wiring through the composition root.
  - [x] **Sub-task 2.4:** Extend canonical diagnostics and operator-facing views so session and summary state are inspectable.

- [x] **Task 3: Make the public conversational API session-first**
  > *Description: Replace the public conversational transport root with `/sessions` and remove `/agent-runs` as the public conversation surface.*
  - [x] **Sub-task 3.1:** Add session routes for create, append, inspect, list items/events, and any required attached conversational execution entrypoints.
  - [x] **Sub-task 3.2:** Update the top-level router so `/sessions` becomes the public conversational root.
  - [x] **Sub-task 3.3:** Remove or demote `/agent-runs` from the public conversational API surface so clients do not have two canonical conversation roots.
  - [x] **Sub-task 3.4:** Preserve structured transport errors and thin-route discipline across the new session routes.

- [x] **Task 4: Add configurable X-turn session summarization**
  > *Description: Implement background-owned session summaries triggered after a configurable number of eligible session turns.*
  - [x] **Sub-task 4.1:** Add a settings field for summary cadence and validate it as a positive integer.
  - [x] **Sub-task 4.2:** Define session summary eligibility and coverage bookkeeping in session-owned logic.
  - [x] **Sub-task 4.3:** Add a versioned summary prompt and persist prompt identity/version with summary state.
  - [x] **Sub-task 4.4:** Schedule summary generation through the background task runner with explicit queued/running/completed/failed state.
  - [x] **Sub-task 4.5:** Emit structured events, diagnostics state, and machine-usable failure codes for summary generation.

- [x] **Task 5: Adapt the current conversational agent to plug into sessions**
  > *Description: Preserve current conversational capability while moving conversation ownership to the new session substrate.*
  - [x] **Sub-task 5.1:** Add an attached-execution seam so the current agent can read from and write to session-owned chronology.
  - [x] **Sub-task 5.2:** Ensure tool calls and results remain explicit and inspectable under the new ownership boundary.
  - [x] **Sub-task 5.3:** Avoid designing deep-research or broader multi-executor orchestration in this sprint.

- [x] **Task 6: Update canonical docs and execution evidence**
  > *Description: Keep docs and sprint evidence aligned with the new ownership boundary and API reality.*
  - [x] **Sub-task 6.1:** Update `backend/docs/api-and-runtime-surfaces.md` and `backend/docs/runtime-overview.md` for the session-first public API.
  - [x] **Sub-task 6.2:** Update `backend/docs/agent-runtime.md` and `backend/docs/codebase-map.md` to reflect session ownership and agent attachment.
  - [x] **Sub-task 6.3:** Record test runs, deferrals, and deviations directly in this tracker as implementation progresses.

## Testing And Documentation Checklist

- [x] **Unit Tests:** deterministic coverage for session ordering, summary eligibility, context assembly, and prompt/version propagation
- [x] **Integration Tests:** session persistence, composition wiring, route behavior, and summary task lifecycle coverage for the sprint scope
- [x] **Smoke Tests:** session create/append/inspect flow and session-backed conversational execution path
- [x] **Real Provider Smoke:** if summary generation is a supported real-provider path in this sprint, run and record at least one real-provider smoke or explicitly justify deferral
- [x] **Documentation Updates:** update canonical documentation in `backend/docs/`

## Risks And Blockers

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| Session migration leaves two canonical public conversation roots | High | Make `/sessions` the only public conversational root in this sprint and update docs/routes together | Open |
| Session substrate accidentally bakes in agent-specific concepts | High | Keep session items neutral and push executor-specific behavior behind attached-execution seams | Open |
| User/org context introduces premature auth or tenancy commitments | Medium | Support optional identifiers and replaceable resolvers only; defer concrete auth semantics | Open |
| Summary generation causes hidden background failures or unclear coverage gaps | High | Use explicit task ownership, summary state, stable codes, and diagnostics surfaces from day one | Open |
| Summary cadence is implemented as a hard-coded constant despite the requirement | Medium | Add settings validation and assert cadence behavior through unit and integration tests | Open |

## Success Criteria

- [x] **Success Criteria 1:** Session becomes the durable conversation root in code, docs, and public API surfaces.
- [x] **Success Criteria 2:** The public conversational API is session-first and no longer exposes `/agent-runs` as the canonical conversation entry surface.
- [x] **Success Criteria 3:** Session summarization runs asynchronously after a configurable number of eligible turns and remains inspectable end-to-end.
- [x] **Success Criteria 4:** The current conversational agent still works by attaching to sessions rather than owning the transcript root.

## Review And Sign-Off

- Sprint Status: Complete
- Completion Date: 2026-04-19

## Execution Evidence

- `git status --short --branch` confirmed work started from `sprint/sprint-04-session-substrate-foundation`.
- Added an initial session substrate (`platform/sessions/`, `modules/sessions/`) and moved the public conversational router root to `/sessions`.
- Added session-backed create/append/get/list-items/list-events/stream/approval/cancel transport surfaces.
- Added SQLAlchemy session records and store wiring plus in-memory session storage for sqlite-backed tests.
- Added attached execution wiring so agent runtime mirrors tool and assistant chronology into session items.
- Added configurable `session_summary_turn_interval`, versioned session summary prompt metadata, materialized summary persistence, and background-owned queued/running/completed/failed summary lifecycle.
- Added session diagnostics to `/system/diagnostics` and updated canonical docs for the session-first public API and agent attachment boundary.
- Verification:
  - `python -m compileall backend/src/hello_sales_backend`
  - `python -m compileall backend/tests`
  - `python -m pytest backend/tests/smoke/test_agent_runs.py backend/tests/integration/test_agent_event_stream.py -q`
  - `python -m pytest backend/tests/smoke/test_agent_runs.py backend/tests/integration/test_agent_event_stream.py backend/tests/smoke/test_system_diagnostics.py backend/tests/integration/test_agent_observability.py -q`
  - `python -m pytest backend/tests -q`
- Real-provider smoke note:
  - The backend smoke suite now covers the provider-backed session-first conversational flow through the existing generic-agent smoke harness. In local test execution this suite passed with the fake provider override and the real-provider cases remain environment-gated as intended.
