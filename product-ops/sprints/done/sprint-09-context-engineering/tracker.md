# Sprint Tracker: Context Engineering

> Project: HelloSales
> Sprint ID: sprint-09-context-engineering
> Created: 2026-04-24

## Sprint Overview

- **Sprint Name:** Context Engineering
- **Sprint Focus:** Build an agent-agnostic context and prompt assembly system that can swap basic session context, memory, and future conversation retrieval options through profiles.
- **Depends On:** `ops/sprints/done/sprint-04-session-substrate-foundation/tracker.md`, `ops/sprints/done/sprint-08-workos-auth-foundation/tracker.md`
- **Status:** Complete

## Sprint Goals

- **Primary Goal:** Extract the current hard-coded agent context path into a flexible, profile-driven context engineering layer.
- **Secondary Goals:**
  - Preserve the current session summary plus recent session item behavior as the default `basic` profile.
  - Add extension points for short-term memory variants, long-term memory, and future conversation RAG without designing RAG primitives.
  - Keep prompt/context strategy selection agent-agnostic and observable.

## Execution Checklist

- [x] **Task 1: Add context engineering contracts and profile models**
  > *Description: Define the stable platform-owned abstractions for context requests, source results, profiles, budgets, and provenance.*
  - [x] **Sub-task 1.1:** Add context build request/result, profile metadata, source result, and budget/provenance models under `platform/agents/`.
  - [x] **Sub-task 1.2:** Define `AgentContextAssembler` and `AgentContextSource` protocols with required/optional failure policy.
  - [x] **Sub-task 1.3:** Add fake/no-op context sources for deterministic unit tests.

- [x] **Task 2: Implement the default basic session context profile**
  > *Description: Move the existing summary plus recent session item logic behind a named replaceable profile without changing default runtime behavior.*
  - [x] **Sub-task 2.1:** Extract `_build_session_context_messages` behavior into a session context source or strategy.
  - [x] **Sub-task 2.2:** Preserve summary coverage filtering, historical-context wording, recent item ordering, and the current recent item limit as profile parameters.
  - [x] **Sub-task 2.3:** Add regression tests proving `basic-session-v1` matches the current message assembly shape.

- [x] **Task 3: Wire context assembly into the agent runtime**
  > *Description: Make `GenericAgentRuntime` delegate context assembly before provider calls while keeping tool replay, approvals, and fallback behavior intact.*
  - [x] **Sub-task 3.1:** Inject the context assembler through runtime construction/composition.
  - [x] **Sub-task 3.2:** Replace inline session context assembly with profile-driven assembly.
  - [x] **Sub-task 3.3:** Emit inspectable run events for selected context profile, source counts, skipped sources, and truncation decisions.

- [x] **Task 4: Add memory and future retrieval extension points**
  > *Description: Make room for short-term memory variants, long-term memory, and parallel RAG work without committing to their storage or indexing design.*
  - [x] **Sub-task 4.1:** Add source categories/scopes for session, summary, semantic memory, episodic memory, procedural memory, and retrieval.
  - [x] **Sub-task 4.2:** Add a fake long-term memory source and test that it can be enabled by profile without changing an agent definition.
  - [x] **Sub-task 4.3:** Add a future retrieval source port that accepts run/session/query metadata and returns ranked context blocks or refs, with no vector/index/chunking implementation.

- [x] **Task 5: Make prompt/context selection agent-agnostic**
  > *Description: Preserve concrete agent prompt ownership while moving cross-cutting context policy to runtime profiles.*
  - [x] **Sub-task 5.1:** Add context profile metadata/version propagation alongside existing effective prompt refs.
  - [x] **Sub-task 5.2:** Wire default profile selection through settings or composition.
  - [x] **Sub-task 5.3:** Test that the same concrete agent definition runs with the basic profile and a fake memory-enabled profile.

- [x] **Task 6: Testing, documentation, and evidence**
  > *Description: Prove the new context layer is replaceable, observable, and behavior-preserving for the default path.*
  - [x] **Sub-task 6.1:** Add unit tests for assembler ordering, budget/truncation behavior, optional source failure, required source failure, and provenance metadata.
  - [x] **Sub-task 6.2:** Add integration coverage for session-backed runtime assembly through the composed app.
  - [x] **Sub-task 6.3:** Run existing agent/session smoke coverage and record real-provider smoke or justified deferral.
  - [x] **Sub-task 6.4:** Update `backend/docs/agent-runtime.md`, `backend/docs/runtime-overview.md`, and `backend/docs/codebase-map.md`.

## Testing And Documentation Checklist

- [x] **Unit Tests:** deterministic coverage for context assembler ordering, profile selection, source failure policy, budget/truncation, and provenance
- [x] **Integration Tests:** composed session-backed agent runtime uses context profiles without private patching
- [x] **Smoke Tests:** session-backed generic agent path still works with the default basic context profile
- [x] **Real Provider Smoke:** completed successfully against the configured Groq provider using the CLI smoke harness.
- [x] **Documentation Updates:** update canonical documentation in `backend/docs/`

## Risks And Blockers

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| Context abstraction becomes too generic to implement cleanly | High | Start by extracting the current behavior into `basic-session-v1`, then generalize only the source/profile boundaries needed for memory/retrieval | Mitigated |
| Default agent behavior changes while extracting context assembly | High | Add regression tests over assembled message structure before adding optional memory/retrieval sources | Mitigated |
| Long-term memory scope is premature | Medium | Add contracts/fakes and scope metadata only; defer durable memory storage decisions | Mitigated |
| Parallel RAG work needs a different retrieval shape | Medium | Keep the retrieval boundary primitive-agnostic and accept ranked blocks or refs rather than vector-store concepts | Mitigated |
| Context events leak sensitive prompt or memory contents | High | Emit profile/source ids, counts, truncation, and provenance metadata without raw private text unless already present in existing inspectable events | Mitigated |

## Success Criteria

- [x] **Success Criteria 1:** `GenericAgentRuntime` no longer hard-codes session context assembly policy.
- [x] **Success Criteria 2:** The default context profile preserves the current session summary plus recent item behavior.
- [x] **Success Criteria 3:** Short-term memory, long-term memory, and future retrieval can be represented as context sources selected by profile.
- [x] **Success Criteria 4:** Context profile/source metadata is inspectable through tests and runtime events.
- [x] **Success Criteria 5:** No RAG primitives are designed or implemented in this sprint.

## Review And Sign-Off

- Sprint Status: Complete
- Completion Date: 2026-04-24

## Execution Evidence

- Created Sprint 9 reasoning and tracker artifacts.
- External research completed on 2026-04-24 and recorded in `reasoning.md`.
- Implemented `platform/agents/context.py` with context profiles, source protocols, source results, budgets, provenance, fake sources, default session source, fake long-term memory source, and future retrieval port.
- Wired `GenericAgentRuntime` and `platform/composition/app_container.py` to use `basic-session-v1` by default through `HELLO_SALES_AGENT_CONTEXT_PROFILE`.
- Added `agent.context.assembled` runtime events with profile/source counts, skipped sources, truncation decisions, and provenance metadata without raw context text.
- Tests run on 2026-04-24:
  - `PYTHONPATH=src pytest tests/unit/test_agent_context.py tests/unit/test_generic_agent_runtime.py` - passed, 22 tests.
  - `ruff check src tests/unit/test_agent_context.py tests/unit/test_generic_agent_runtime.py` - passed.
  - `mypy src/hello_sales_backend/platform/agents src/hello_sales_backend/platform/composition/app_container.py src/hello_sales_backend/platform/config/settings.py` - passed.
  - `PYTHONPATH=src pytest tests/integration/test_app_factory.py tests/integration/test_agent_event_stream.py tests/smoke/test_agent_runs.py tests/smoke/test_session_summary_smoke.py` - passed, 7 tests.
  - `ruff check src tests` - passed.
  - `mypy src` - passed, 234 source files.
  - `PYTHONPATH=src pytest tests/unit tests/integration tests/smoke` - passed, 125 passed and 6 skipped.
  - `PYTHONPATH=src pytest tests/smoke` - passed after env updates, 10 passed and 5 skipped.
  - `PYTHONPATH=src pytest tests/postgres` - 2 skipped because Postgres-specific tests were not enabled by the local environment.
  - `HELLO_SALES_AUTH_REQUIRED=false PYTHONPATH=src python -m hello_sales_backend.smoke generic-agent-provider` - passed against `provider=groq`, `model=openai/gpt-oss-20b`.
- Documentation updated:
  - `backend/docs/agent-runtime.md`
  - `backend/docs/runtime-overview.md`
  - `backend/docs/codebase-map.md`
  - `backend/docs/configuration-and-environment.md`
- Real-provider smoke attempt notes:
  - `backend/.env` contains provider and Tavily credentials, so the earlier credential-based deferral was removed.
  - The CLI smoke harness now injects a local smoke auth provider when `HELLO_SALES_AUTH_REQUIRED=false`, which fixes the earlier `auth.unauthenticated` failure mode for smoke execution.
  - The approval-boundary scenario was made more deterministic by retrying explicit approval-gated prompts and falling back to an approval-gated analytics query prompt when `run_diagnostic_job` model selection was inconsistent.
  - Final successful provider-backed smoke output included completed scenarios for `generic_status_completion`, `observer_status_completion`, `append_turn_completion`, `approval_boundary`, `event_stream_replay`, and `analytics_query_completion`.
