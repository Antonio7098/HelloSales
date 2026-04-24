# Sprint Tracker: Context Engineering

> Project: HelloSales
> Sprint ID: sprint-09-context-engineering
> Created: 2026-04-24

## Sprint Overview

- **Sprint Name:** Context Engineering
- **Sprint Focus:** Build an agent-agnostic context and prompt assembly system that can swap basic session context, memory, and future conversation retrieval options through profiles.
- **Depends On:** `ops/sprints/sprint-04-session-substrate-foundation/tracker.md`, `ops/sprints/sprint-08-workos-auth-foundation/tracker.md`
- **Status:** Not Started

## Sprint Goals

- **Primary Goal:** Extract the current hard-coded agent context path into a flexible, profile-driven context engineering layer.
- **Secondary Goals:**
  - Preserve the current session summary plus recent session item behavior as the default `basic` profile.
  - Add extension points for short-term memory variants, long-term memory, and future conversation RAG without designing RAG primitives.
  - Keep prompt/context strategy selection agent-agnostic and observable.

## Execution Checklist

- [ ] **Task 1: Add context engineering contracts and profile models**
  > *Description: Define the stable platform-owned abstractions for context requests, source results, profiles, budgets, and provenance.*
  - [ ] **Sub-task 1.1:** Add context build request/result, profile metadata, source result, and budget/provenance models under `platform/agents/`.
  - [ ] **Sub-task 1.2:** Define `AgentContextAssembler` and `AgentContextSource` protocols with required/optional failure policy.
  - [ ] **Sub-task 1.3:** Add fake/no-op context sources for deterministic unit tests.

- [ ] **Task 2: Implement the default basic session context profile**
  > *Description: Move the existing summary plus recent session item logic behind a named replaceable profile without changing default runtime behavior.*
  - [ ] **Sub-task 2.1:** Extract `_build_session_context_messages` behavior into a session context source or strategy.
  - [ ] **Sub-task 2.2:** Preserve summary coverage filtering, historical-context wording, recent item ordering, and the current recent item limit as profile parameters.
  - [ ] **Sub-task 2.3:** Add regression tests proving `basic-session-v1` matches the current message assembly shape.

- [ ] **Task 3: Wire context assembly into the agent runtime**
  > *Description: Make `GenericAgentRuntime` delegate context assembly before provider calls while keeping tool replay, approvals, and fallback behavior intact.*
  - [ ] **Sub-task 3.1:** Inject the context assembler through runtime construction/composition.
  - [ ] **Sub-task 3.2:** Replace inline session context assembly with profile-driven assembly.
  - [ ] **Sub-task 3.3:** Emit inspectable run events for selected context profile, source counts, skipped sources, and truncation decisions.

- [ ] **Task 4: Add memory and future retrieval extension points**
  > *Description: Make room for short-term memory variants, long-term memory, and parallel RAG work without committing to their storage or indexing design.*
  - [ ] **Sub-task 4.1:** Add source categories/scopes for session, summary, semantic memory, episodic memory, procedural memory, and retrieval.
  - [ ] **Sub-task 4.2:** Add a fake long-term memory source and test that it can be enabled by profile without changing an agent definition.
  - [ ] **Sub-task 4.3:** Add a future retrieval source port that accepts run/session/query metadata and returns ranked context blocks or refs, with no vector/index/chunking implementation.

- [ ] **Task 5: Make prompt/context selection agent-agnostic**
  > *Description: Preserve concrete agent prompt ownership while moving cross-cutting context policy to runtime profiles.*
  - [ ] **Sub-task 5.1:** Add context profile metadata/version propagation alongside existing effective prompt refs.
  - [ ] **Sub-task 5.2:** Wire default profile selection through settings or composition.
  - [ ] **Sub-task 5.3:** Test that the same concrete agent definition runs with the basic profile and a fake memory-enabled profile.

- [ ] **Task 6: Testing, documentation, and evidence**
  > *Description: Prove the new context layer is replaceable, observable, and behavior-preserving for the default path.*
  - [ ] **Sub-task 6.1:** Add unit tests for assembler ordering, budget/truncation behavior, optional source failure, required source failure, and provenance metadata.
  - [ ] **Sub-task 6.2:** Add integration coverage for session-backed runtime assembly through the composed app.
  - [ ] **Sub-task 6.3:** Run existing agent/session smoke coverage and record real-provider smoke or justified deferral.
  - [ ] **Sub-task 6.4:** Update `backend/docs/agent-runtime.md`, `backend/docs/runtime-overview.md`, and `backend/docs/codebase-map.md`.

## Testing And Documentation Checklist

- [ ] **Unit Tests:** deterministic coverage for context assembler ordering, profile selection, source failure policy, budget/truncation, and provenance
- [ ] **Integration Tests:** composed session-backed agent runtime uses context profiles without private patching
- [ ] **Smoke Tests:** session-backed generic agent path still works with the default basic context profile
- [ ] **Real Provider Smoke:** run if provider credentials are available and provider-facing message assembly materially changed; otherwise record explicit deferral
- [ ] **Documentation Updates:** update canonical documentation in `backend/docs/`

## Risks And Blockers

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| Context abstraction becomes too generic to implement cleanly | High | Start by extracting the current behavior into `basic-session-v1`, then generalize only the source/profile boundaries needed for memory/retrieval | Open |
| Default agent behavior changes while extracting context assembly | High | Add regression tests over assembled message structure before adding optional memory/retrieval sources | Open |
| Long-term memory scope is premature | Medium | Add contracts/fakes and scope metadata only; defer durable memory storage decisions | Open |
| Parallel RAG work needs a different retrieval shape | Medium | Keep the retrieval boundary primitive-agnostic and accept ranked blocks or refs rather than vector-store concepts | Open |
| Context events leak sensitive prompt or memory contents | High | Emit profile/source ids, counts, truncation, and provenance metadata without raw private text unless already present in existing inspectable events | Open |

## Success Criteria

- [ ] **Success Criteria 1:** `GenericAgentRuntime` no longer hard-codes session context assembly policy.
- [ ] **Success Criteria 2:** The default context profile preserves the current session summary plus recent item behavior.
- [ ] **Success Criteria 3:** Short-term memory, long-term memory, and future retrieval can be represented as context sources selected by profile.
- [ ] **Success Criteria 4:** Context profile/source metadata is inspectable through tests and runtime events.
- [ ] **Success Criteria 5:** No RAG primitives are designed or implemented in this sprint.

## Review And Sign-Off

- Sprint Status: Not Started
- Completion Date: [Date]

## Execution Evidence

- Created Sprint 9 reasoning and tracker artifacts.
- External research completed on 2026-04-24 and recorded in `reasoning.md`.
- [Record implementation test runs, smoke evidence, documentation updates, explicit deferrals, and review notes here as execution progresses.]
