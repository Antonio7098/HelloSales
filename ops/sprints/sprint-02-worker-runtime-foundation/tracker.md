# Sprint Tracker: Worker Runtime Foundation

> Project: HelloSales
> Sprint ID: sprint-02-worker-runtime-foundation
> Created: 2026-04-16

## Sprint Overview

- **Sprint Name:** Worker Runtime Foundation
- **Sprint Focus:** Introduce a bounded worker runtime as a sibling to the conversational agent runtime, while extracting a neutral LLM substrate and preserving pre-brief architectural discipline.
- **Depends On:** `ops/sprints/sprint-01-observability-foundation`
- **Status:** Not Started

## Sprint Goals

- **Primary Goal:** Establish the first worker-runtime foundation with explicit contracts, bounded retries, timeout control, local structured-output validation, and a narrow operational surface.
- **Secondary Goals:**
  - Extract provider and JSON-generation mechanics into a neutral `platform/llm/` layer without broadening product-specific scope.
  - Keep `platform/agents/`, `application/agents/`, and `modules/agent_runs/` conversational-only and free from worker semantics.
  - Make worker execution safe to invoke from Stageflow orchestration without formalising planner/fan-out as a first-class generic runtime pattern.

## Execution Checklist

- [ ] **Task 1: Add the worker operational contract first**
  > *Description: Define the normative rules for worker runtime behavior before implementation so the sprint has an explicit contract for structured output, retries, timeout semantics, and operational exposure.*
  - [ ] **Sub-task 1.1:** Add `ops/operational-contract/workers.md` covering worker/runtime-policy separation, structured input-output boundaries, local validation authority, retry-timeout-fallback seams, inspectable runs/events, and module-owned operational exposure.
  - [ ] **Sub-task 1.2:** Cross-link `workers.md` from `ops/operational-contract/README.md` and ensure the wording stays complementary to `agents.md` rather than overlapping or conflicting with it.

- [ ] **Task 2: Extract a neutral LLM substrate**
  > *Description: Move provider-facing mechanics out of the agent runtime into a domain-neutral platform LLM layer that both agents and workers can consume through stable contracts.*
  - [ ] **Sub-task 2.1:** Introduce `platform/llm/` contracts, response models, call context, and JSON schema helpers for text and JSON generation without embedding worker-specific retry or fallback policy.
  - [ ] **Sub-task 2.2:** Rehome the current OpenAI-compatible provider logic under `platform/llm/providers/` and preserve transport-level timeout and retryable-provider classification behavior.

- [ ] **Task 3: Preserve the agent runtime as conversational-only**
  > *Description: Repoint the existing agent runtime to the new neutral LLM substrate without teaching the agent stack about worker concepts such as structured output contracts, artifacts-as-output, or worker retries.*
  - [ ] **Sub-task 3.1:** Update `platform/agents/` and `application/agents/` imports and contracts so the agent runtime depends on the neutral LLM substrate with no functional expansion beyond dependency cleanup.
  - [ ] **Sub-task 3.2:** Verify that `modules/agent_runs/` remains turn-based, tool-oriented, approval-aware, and conversational-only after the substrate extraction.

- [ ] **Task 4: Add the worker runtime core**
  > *Description: Introduce separate worker runtime models, persistence seams, validation flow, and execution semantics with bounded invocation behavior and no tool or artifact abstractions.*
  - [ ] **Sub-task 4.1:** Add `platform/workers/` models, contracts, persistence ports, execution runtime seams, and explicit worker lifecycle state covering pending/running/retrying/completed/failed/cancelled behavior as needed.
  - [ ] **Sub-task 4.2:** Add `application/workers/` contracts and registry scaffolding so concrete worker definitions can live outside generic runtime code.
  - [ ] **Sub-task 4.3:** Implement local JSON parsing and structured validation flow for worker outputs, with bounded corrective retries and optional final-attempt backup model/provider selection.

- [ ] **Task 5: Add a narrow worker operational surface**
  > *Description: Expose worker runtime behavior through a dedicated application module and minimal operational API rather than through agent surfaces or speculative product endpoints.*
  - [ ] **Sub-task 5.1:** Add `modules/worker_runs/` with use cases and views for starting a worker run, inspecting status, listing events, and cancelling a run if still active.
  - [ ] **Sub-task 5.2:** Keep transport exposure intentionally narrow and operational, and ensure worker state is inspectable without introducing broad product-facing endpoints.

- [ ] **Task 6: Add provider JSON-mode support with provider-specific strictness handling**
  > *Description: Support provider-native JSON output in the neutral LLM layer while keeping correctness in local validation rather than in provider strictness alone.*
  - [ ] **Sub-task 6.1:** Add JSON-generation support to the OpenAI-compatible adapter using `json_object` by default and schema hints where supported.
  - [ ] **Sub-task 6.2:** Keep strict/non-strict schema handling inside the provider adapter so provider quirks do not leak into worker or agent runtime policy.

- [ ] **Task 7: Make worker execution callable from Stageflow without over-formalising orchestration**
  > *Description: Ensure workers can be invoked cleanly from Stageflow parent pipelines and child subpipelines while deferring any generic planner/fan-out framework.*
  - [ ] **Sub-task 7.1:** Add worker-runtime integration points that allow Stageflow stages or child pipelines to invoke workers through app-owned boundaries.
  - [ ] **Sub-task 7.2:** Preserve explicit timeout, retry, cancellation, and inspectable run-state behavior for Stageflow-driven worker execution.

- [ ] **Task 8: Validate, document, and prepare for review**
  > *Description: Add executable evidence and documentation so the new worker-runtime foundation is reviewable, operationally visible, and safe to extend in later sprints.*
  - [ ] **Sub-task 8.1:** Add unit, integration, smoke, and failure-path verification for worker execution, JSON-mode provider paths, retries, timeout handling, fallback selection, and Stageflow compatibility.
  - [ ] **Sub-task 8.2:** Update `backend/docs/` to explain the new `platform/llm/` substrate, the worker runtime boundary, and the relationship between workers, agents, and workflows.

## Testing And Documentation Checklist

- [ ] **Unit Tests:** deterministic coverage for LLM substrate contracts, JSON schema normalization, worker validation/retry policy, provider strict/non-strict handling, and worker registry/runtime logic
- [ ] **Integration Tests:** persistence, module wiring, operational worker surfaces, and Stageflow compatibility through realistic runtime seams
- [ ] **Smoke Tests With Real Provider:** add or extend real-provider smoke coverage for the worker JSON-generation path and keep the supported conversational baseline smoke passing
- [ ] **Documentation Updates:** update canonical docs in `docs/` plus operational/process artifacts as needed

## Risks And Blockers

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| Shared LLM extraction accidentally leaks worker semantics back into the conversational agent runtime | High | Keep text and JSON generation generic in `platform/llm/`; keep retries, validation, and fallback policy in `platform/workers/` | Open |
| OpenAI-compatible providers behave inconsistently for strict JSON schema mode | High | Treat provider-side strictness as transport guidance only; validate locally and keep adapter-specific strict/non-strict choices isolated in provider code | Open |
| Worker operational scope expands into speculative product APIs before the brief | Medium | Keep worker exposure minimal and operational-only through `modules/worker_runs/` and narrow transport surfaces | Open |
| Stageflow integration drifts into a generic planner/fan-out framework too early | Medium | Limit the sprint to worker invocation compatibility and explicit child-run inspectability; defer planner abstractions | Open |
| Retry and fallback behavior becomes hidden or untestable | High | Record explicit lifecycle events, bounded attempt counts, backup-provider selection rules, and failure-path tests | Open |

## Success Criteria

- [ ] **Success Criteria 1:** The backend has a neutral `platform/llm/` substrate that can serve both conversational agents and structured workers without coupling the two runtimes together.
- [ ] **Success Criteria 2:** A separate worker runtime exists with explicit run state, local structured-output validation, bounded retries/timeouts, optional fallback selection, and a narrow operational module surface.
- [ ] **Success Criteria 3:** Reviewable evidence exists through tests, runtime surfaces, and updated backend docs, and the agent runtime remains conversational-only after the extraction.

## Review And Sign-Off

- Sprint Status: Not Started
- Completion Date: [Date]
