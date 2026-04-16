# Sprint Reasoning: Worker Runtime Foundation

> Project: HelloSales
> Sprint ID: sprint-02-worker-runtime-foundation
> Output: `ops/sprints/sprint-02-worker-runtime-foundation/reasoning.md`

## Overview

**Sprint:** Worker Runtime Foundation
**Purpose:** Introduce a structured worker runtime as a sibling to the conversational agent runtime, grounded in a neutral LLM substrate and explicit pre-brief operational scaffolding.
**Tracker:** `ops/sprints/sprint-02-worker-runtime-foundation/tracker.md`
**Depends On:** `ops/sprints/sprint-01-observability-foundation/tracker.md`

## Requirement Map

### Contract Coverage Reviewed For This Sprint

| Contract File | Area | Applicability | Why It Matters |
| --- | --- | --- | --- |
| `ops/operational-contract/README.md` | Contract usage model | Applicable | Confirms process artifacts should map sprint scope to whichever contracts apply, rather than hard-coding one contract family. |
| `ops/operational-contract/architecture.md` | Layering and dependency direction | Applicable | The sprint extracts a shared substrate, preserves module boundaries, and adds a new module/runtime family. |
| `ops/operational-contract/errors.md` | Failure shape and retry visibility | Applicable | Workers introduce timeout, retry, provider fallback, and structured validation failure paths. |
| `ops/operational-contract/observability.md` | Signals, correlation, diagnostics | Applicable | Worker runs and fallback behavior must be inspectable and correlated. |
| `ops/operational-contract/testing.md` | Test seams and evidence expectations | Applicable | The sprint changes provider paths, wiring, persistence, and failure behavior. |
| `ops/operational-contract/workflows.md` | Stageflow eligibility and lifecycle semantics | Applicable | Worker execution must be callable from Stageflow without leaking engine internals or inventing premature planner abstractions. |
| `ops/operational-contract/agents.md` | Agent runtime boundaries | Applicable | The sprint must preserve agents as conversational-only and avoid collapsing workers into the agent model. |
| `ops/operational-contract/pre-brief-scope.md` | Scaffold-stage limits | Applicable | This is pre-brief infrastructure work and must avoid product commitments or broad public APIs. |

### Requirement Index Used In This Sprint

| Requirement ID | Title | Area | Applicability | Why It Matters For This Sprint |
| --- | --- | --- | --- | --- |
| PRE-SCOPE-001 | Foundation work may proceed before the brief | Pre-Brief Scope | Applicable | Shared LLM plumbing, worker runtime seams, task/state models, and docs are safe scaffold-stage work. |
| PRE-SCOPE-002 | Product-specific commitments must wait for the brief | Pre-Brief Scope | Applicable | The sprint must avoid domain-specific worker schemas, planner products, or broad product APIs. |
| PRE-SCOPE-003 | Operational scaffolding should be favored over product assumptions | Pre-Brief Scope | Applicable | The whole sprint is about reusable runtime scaffolding, observability, and replaceable adapters. |
| PRE-SCOPE-004 | Public APIs must remain intentionally narrow before the brief | Pre-Brief Scope | Applicable | Worker exposure must remain operational-only and narrow. |
| ARCH-CORE-001 | Module boundaries must remain explicit | Architecture | Applicable | The sprint introduces `platform/workers`, `application/workers`, and `modules/worker_runs/`. |
| ARCH-CORE-002 | Dependency direction must point inward | Architecture | Applicable | Shared provider logic must move downward into a neutral layer without use-case or route leakage. |
| ARCH-LAYER-002 | Use cases depend on ports, not infra | Architecture | Applicable | Worker services should depend on provider/store/runtime ports rather than concrete adapters. |
| ARCH-ENTRY-001 | Transport adapters must stay thin | Architecture | Applicable | Worker operational routes must stay adapter-thin if exposed this sprint. |
| ARCH-MODULE-001 | Module public APIs must stay small and stable | Architecture | Applicable | `modules/worker_runs/` must expose a narrow service/facade, not repos or provider internals. |
| ARCH-COMP-001 | Composition must happen through registrars | Architecture | Applicable | New worker and LLM substrate wiring must flow through composition/bootstrap. |
| ARCH-SHARED-001 | Shared and platform code must stay domain-neutral | Architecture | Applicable | `platform/llm/` and `platform/workers/` must remain generic and product-neutral. |
| ERR-CORE-001 | No failure may disappear | Errors | Applicable | Worker validation, provider, timeout, retry, and fallback failures must all remain explicit and inspectable. |
| ERR-SHAPE-001 | Operational errors must preserve the canonical shape | Errors | Applicable | Worker and provider failures must preserve stable codes, details, and context. |
| ERR-TRANS-001 | Error translation must preserve cause and context | Errors | Applicable | Parsing, validation, provider, and workflow errors will cross multiple layers. |
| ERR-BG-001 | Background work must end in explicit inspectable failure state | Errors | Applicable | Worker runs will likely execute through the task runner or workflow runtime and need explicit terminal state. |
| ERR-PROVIDER-001 | Provider failures must remain classified and observable | Errors | Applicable | Provider-native JSON output, timeouts, and fallback selection are central sprint behavior. |
| ERR-DATA-001 | Persistence and data failures must be loud and distinct | Errors | Applicable | Worker run/result persistence must not hide storage failures as validation or not-found behavior. |
| ERR-REDACT-001 | Redaction must protect secrets without destroying diagnosis | Errors | Applicable | Provider payload details and error context must stay redacted but useful. |
| OBS-CORE-001 | Failures must produce structured operational signals | Observability | Applicable | Worker retries, fallback, cancellation, and failure outcomes must be visible. |
| OBS-CORR-001 | Correlation identifiers must survive subsystem boundaries | Observability | Applicable | Worker runs, provider calls, and Stageflow invocations should preserve request/trace metadata. |
| OBS-DIAG-001 | Diagnostics surfaces must expose operator-relevant state | Observability | Applicable | Worker run status and recent failure state should be inspectable through canonical operational paths. |
| OBS-BG-001 | Background work must have visible terminal state | Observability | Applicable | Worker execution must not become fire-and-forget. |
| OBS-ALERT-001 | High-severity signals must be machine-usable for alerting | Observability | Applicable | Stable codes are needed for provider retry exhaustion, validation exhaustion, and worker run failure. |
| TEST-SEAM-001 | Collaborators must be replaceable through public seams | Testing | Applicable | Providers, stores, registries, and runtime policies must be easy to fake without private patching. |
| TEST-UNIT-001 | Business logic must have unit coverage | Testing | Applicable | Retry policy, validation flow, and provider JSON formatting are deterministic and should be unit-tested. |
| TEST-INT-001 | Wiring and persistence changes must have integration coverage | Testing | Applicable | New modules, stores, and composition wiring require integration tests. |
| TEST-SMOKE-001 | Critical runtime paths must have smoke coverage | Testing | Applicable | Worker invocation and baseline runtime behavior should have smoke coverage. |
| TEST-SMOKE-002 | Critical external provider paths must have real-provider smoke coverage | Testing | Applicable | The new worker JSON-provider path is a supported provider-backed runtime path. |
| TEST-FAIL-001 | Failure paths must be tested explicitly | Testing | Applicable | Invalid JSON, validation failure, provider timeout, fallback selection, and persistence errors are core sprint failure modes. |
| TEST-DET-001 | Tests must remain deterministic and non-brittle | Testing | Applicable | Assertions should target lifecycle, structure, and stable codes rather than model phrasing. |
| WF-SCOPE-001 | Workflows must be used only for real orchestration | Workflows | Applicable | The sprint should support Stageflow invocation without introducing a workflow where a direct service call suffices. |
| WF-BOUNDARY-001 | Workflow engines must stay behind app-owned boundaries | Workflows | Applicable | Worker invocation must use app-owned runtime/facade seams, not raw Stageflow internals across ordinary services. |
| WF-STATE-001 | Workflow outcomes must be explicit and inspectable | Workflows | Applicable | Stageflow-driven worker runs still need explicit worker terminal state and event visibility. |
| WF-RETRY-001 | Retry and cancellation semantics must be explicit | Workflows | Applicable | Worker retry/timeouts must be explicit whether invoked directly or from Stageflow. |
| AGENT-BOUNDARY-001 | Runtime mechanics and policy must stay separate | Agents | Applicable | The sprint must not push worker policy into generic agent runtime packages. |
| AGENT-TOOL-001 | Tool execution boundaries must stay explicit | Agents | Applicable | The sprint should preserve tools as agent-only rather than making them part of the worker runtime. |
| AGENT-RUN-001 | Runs and events must be persisted or inspectable | Agents | Applicable | Agent inspectability must remain intact while shared LLM mechanics move out. |
| AGENT-LIFECYCLE-001 | Approval, cancellation, and resume seams must stay explicit | Agents | Applicable | Agent behavior must remain unchanged and explicit after substrate extraction. |
| AGENT-EXPOSE-001 | Operational exposure must flow through application modules | Agents | Applicable | Worker exposure should mirror this principle through a dedicated module instead of transport reaching into platform code. |

### Applicable Requirements

- **PRE-SCOPE-001 / PRE-SCOPE-003:** This sprint is legitimate pre-brief foundation work because it focuses on scaffolding, seams, retries, observability, and runtime replaceability rather than product-specific worker behavior.
- **PRE-SCOPE-002 / PRE-SCOPE-004:** The sprint must stop at generic worker infrastructure, one sample scaffold if needed, and narrow operational exposure; it must not invent business workflows, business schemas, or broad public APIs.
- **ARCH-CORE-001 / ARCH-COMP-001 / ARCH-SHARED-001:** New worker and LLM substrate packages must have explicit ownership boundaries and be assembled through composition rather than route-level wiring or platform/agent leakage.
- **ARCH-CORE-002 / ARCH-LAYER-002:** Use cases must depend on ports, and the shared LLM substrate must remain inward-facing and generic rather than being a provider-specific or route-owned convenience layer.
- **ERR-CORE-001 / ERR-PROVIDER-001 / ERR-BG-001:** Worker timeout, retry, parsing, validation, and fallback behavior must all end in explicit, inspectable terminal state with stable codes and visible attempt context.
- **OBS-CORE-001 / OBS-CORR-001 / OBS-BG-001 / OBS-DIAG-001:** Worker runs must emit inspectable events and preserve request/trace metadata across background and Stageflow boundaries.
- **TEST-SEAM-001 / TEST-INT-001 / TEST-SMOKE-002 / TEST-FAIL-001:** Because the sprint changes both runtime wiring and real-provider behavior, it requires unit, integration, smoke, and explicit negative-path verification.
- **WF-BOUNDARY-001 / WF-RETRY-001:** Worker runtime must be callable from Stageflow but still own its own retry/timeout semantics through app-owned seams.
- **AGENT-BOUNDARY-001 / AGENT-EXPOSE-001:** The existing agent stack must remain conversational-only and must not become a dumping ground for worker semantics.

### Non-Applicable Requirements

- **OBS-HEALTH-001:** Worker runtime work does not materially change health/readiness semantics in this sprint, though readiness may eventually reflect provider/configuration sanity if worker execution becomes required for core service operation.
- **ERR-HTTP-001:** Transport error mapping matters only for the narrow operational worker surface, not as the primary complexity driver of this sprint.
- **WF-SCOPE-001 for planner abstraction:** A generic planner/fan-out framework is explicitly out of scope; only worker invocation compatibility matters.

### Ambiguous Or Conflicting Requirements

- **No existing worker-specific contract:** Current operational contracts strongly constrain the sprint, but none explicitly define worker runtime behavior. The safe resolution is to make `ops/operational-contract/workers.md` the first deliverable of the sprint rather than infering worker rules ad hoc.
- **ERR-PROVIDER-001 and provider-side strict JSON mode:** The contract requires clear retry and observability boundaries, but provider strictness varies across OpenAI-compatible backends. The safe interpretation is to keep provider-side strictness as an optimization at the adapter edge and keep local validation authoritative in the worker runtime.
- **WF-BOUNDARY-001 and Stageflow fan-out helpers:** The sprint should allow worker invocation from Stageflow, but formalising planner/fan-out as a generic runtime pattern would overreach pre-brief scope. The safe interpretation is compatibility without framework-level planner abstractions.

### Open Questions

- Should the sprint include one obviously generic sample worker definition for end-to-end smoke coverage, or should it stop at runtime and module scaffolding with test doubles only?
- Should worker run persistence store the final validated output directly on the run record, or as a separate result record tied one-to-one to the run?
- Should provider transport retries live inside each adapter or in a tiny shared wrapper around provider calls, provided the behavior remains adapter-neutral and observable?

### Resolved Decisions

- **Core boundary decision:** Treat agents and workers as sibling runtimes over a shared LLM substrate.
- **Validation authority:** Use provider-native JSON mode where available, but keep local parsing and validation authoritative.
- **Retry layering:** Keep transport retry at the provider edge, but keep structured-output and semantic retry policy in the worker runtime.
- **Stageflow stance:** Support worker invocation from Stageflow, but do not formalise planner/fan-out as a generic runtime pattern in this sprint.
- **Operational stance:** Expose workers through a separate `modules/worker_runs/` operational module, not through `agent_runs` and not through speculative product APIs.

## Feature Analysis

### Feature 1: Worker Contract And Boundary Definition

**Description:** Add a worker-specific operational contract and define the package/module boundary that separates conversational agents, structured workers, and shared LLM mechanics.

**Affected Areas**
- `ops/operational-contract/workers.md`
- `ops/operational-contract/README.md`
- `backend/src/hello_sales_backend/platform/agents/`
- `backend/src/hello_sales_backend/platform/workers/`
- `backend/src/hello_sales_backend/platform/llm/`

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| PRE-SCOPE-003 | Prefer reusable scaffolding and clear seams | Worker/runtime contract and package split | New contract + package ownership review |
| ARCH-CORE-001 | Keep module/runtime boundaries explicit | Separate `agents`, `workers`, and `llm` areas | File ownership and import review |
| ARCH-SHARED-001 | Keep platform code domain-neutral | `platform/llm/` and `platform/workers/` remain generic | Review of package contents and imports |
| AGENT-BOUNDARY-001 | Keep agent-specific behavior out of generic runtime code | Agents remain conversational-only | No worker concepts in agent runtime after extraction |
| AGENT-EXPOSE-001 | Operational exposure must flow through modules | Worker operational surface goes through `modules/worker_runs/` | Module bootstrap/service review |

**Current-System Analysis**
- Today the repo already has a clear agent stack: `platform/agents/`, `application/agents/`, and `modules/agent_runs/`.
- The current provider contract is chat-only in [`backend/src/hello_sales_backend/platform/providers/llm/contracts.py`](/home/antonioborgerees/coding/HelloSales/backend/src/hello_sales_backend/platform/providers/llm/contracts.py:1), which biases the whole runtime surface toward conversational output.
- The current agent runtime in [`backend/src/hello_sales_backend/platform/agents/runtime.py`](/home/antonioborgerees/coding/HelloSales/backend/src/hello_sales_backend/platform/agents/runtime.py:1) is explicitly turn-based, tool-aware, and response-text oriented.
- Those nouns are already semantically agentic. Extending them to mean worker execution would blur runtime identity and violate the design decision we just settled.

**Options Considered**
- **Option A:** Add `worker` as a call mode inside the existing agent runtime.
- **Option B:** Create sibling `workers` and `agents` runtimes over a shared generic LLM layer.
- **Option C:** Skip a shared substrate and build workers as a fully separate vertical with its own providers.

**Chosen Approach**
- Adopt Option B: sibling runtimes over a shared LLM substrate, with a worker-specific operational contract added first.

**Decision Justification**
- Option B best satisfies `AGENT-BOUNDARY-001` because it avoids forcing worker semantics into the agent runtime while still allowing provider reuse.
- Option A would keep `AgentRun`, `AgentTurn`, `response_text`, approvals, and tools as the conceptual center, which is the wrong abstraction for structured workers.
- Option C would avoid mixing, but it would duplicate provider and JSON-mode mechanics and weaken `PRE-SCOPE-003` by reducing replaceability and shared scaffolding.
- Adding `workers.md` first is justified because the repo already treats contracts as normative process inputs; implementing worker behavior without one would create a process hole.

**Execution Notes**
- Keep the worker contract complementary to `agents.md`; do not duplicate agent-tool or approval semantics into worker language.
- The worker contract should explicitly rule out tools and artifacts if those are intentionally conversational-only in this design.

**Expected Evidence**
- **Tests:** none directly for the contract file, but follow-on tests must align with the lifecycle and retry seams it defines.
- **Runtime Evidence:** not applicable for the contract file itself.
- **Review Checks:** worker semantics are not implemented via agent runtime flags or overloaded agent models.

---

### Feature 2: Neutral LLM Substrate Extraction

**Description:** Extract provider-facing mechanics into a generic `platform/llm/` layer that supports both text and JSON generation without embedding worker policy.

**Affected Areas**
- `backend/src/hello_sales_backend/platform/llm/`
- `backend/src/hello_sales_backend/platform/providers/llm/` or its successors under `platform/llm/providers/`
- `backend/src/hello_sales_backend/platform/agents/`
- composition and provider bootstrap wiring

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-CORE-002 | Dependency direction must point inward | Shared provider logic must move to a neutral lower layer | Import direction review |
| ARCH-LAYER-002 | Use cases depend on ports, not infra | Agent/worker runtimes depend on LLM ports, not concrete providers | Constructor/port tests |
| ARCH-COMP-001 | Compose through registrars | Provider/runtime assembly stays in composition | Integration tests for container wiring |
| ARCH-SHARED-001 | Platform remains domain-neutral | `platform/llm/` stays free of agent/worker policy | Package review |
| ERR-PROVIDER-001 | Provider failures classified and observable | Shared provider responses and error mapping stay explicit | Unit tests + error shape checks |
| OBS-CORR-001 | Correlation survives boundaries | Provider call context carries request/trace metadata | Provider call tests/log evidence |

**Current-System Analysis**
- The current chat-only provider contract and adapter are in `platform/providers/llm/`.
- The OpenAI-compatible adapter already captures provider, model, timeout, response status, and request metadata in structured errors, which is useful behavior to preserve.
- The agent runtime consumes the provider directly and assumes text output only.
- The `soft-skills` reference system uses a lower-level provider contract that separates JSON completion from tool completion and text streaming. That shape is closer to what this sprint needs.

**Options Considered**
- **Option A:** Keep the current chat-only contract and layer JSON behavior directly into worker runtime code.
- **Option B:** Extract a neutral LLM substrate with separate text and JSON generation operations.
- **Option C:** Create a worker-only provider contract and leave agents on the current chat contract.

**Chosen Approach**
- Adopt Option B: create a neutral LLM substrate with separate text and JSON generation contracts and shared provider response models.

**Decision Justification**
- Option B keeps shared concerns shared: request/response normalization, schema hints, provider timeouts, and provider error classification belong below both runtimes.
- Option A would place too much provider knowledge into the worker runtime and make provider quirks harder to centralize.
- Option C would avoid some migration work but leave the repo with split provider abstractions and duplicated adapter logic.
- The substrate must remain generic: it should expose JSON-mode request semantics, not worker retry policy or worker validation behavior.

**Execution Notes**
- Start with the smallest contract that covers this sprint: `generate_text(...)`, `generate_json(...)`, call context, response models, and schema helper.
- Do not move semantic retry or fallback policy into the substrate.
- Preserve existing provider error detail and redaction discipline during extraction.

**Expected Evidence**
- **Tests:** unit tests for response models, JSON schema normalization, provider JSON request formatting, and provider error mapping.
- **Runtime Evidence:** provider errors continue to include stable codes, model/provider metadata, timeout values, and remote status/request ids where available.
- **Review Checks:** neither agent nor worker runtime contains provider-specific JSON request-shaping logic.

---

### Feature 3: Worker Runtime Core

**Description:** Add the worker runtime, its models and ports, local validation flow, bounded retries/timeouts, and optional backup provider/model selection.

**Affected Areas**
- `backend/src/hello_sales_backend/platform/workers/`
- `backend/src/hello_sales_backend/application/workers/`
- persistence layer and DB mappings
- task runner integration

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| PRE-SCOPE-001 | Foundation work may proceed | Generic worker runtime scaffolding | Package ownership and scope review |
| PRE-SCOPE-002 | Avoid product commitments | Generic worker schemas and sample definitions only | Review of model/generality |
| ERR-CORE-001 | No failure may disappear | Validation, timeout, retry, and fallback outcomes must be explicit | Failure-path tests and run state |
| ERR-BG-001 | Background work must end in explicit inspectable state | Worker runs need terminal status, timestamps, and attempt state | Integration tests + diagnostics |
| ERR-PROVIDER-001 | Provider failures must remain classified | Provider timeout and retry exhaustion remain visible | Negative tests and event/log review |
| OBS-CORE-001 | Emit structured operational signals | Worker lifecycle and retry events must be inspectable | Event tests and views |
| OBS-BG-001 | Background work visible terminal state | Worker runs cannot be fire-and-forget | Operational view tests |
| TEST-SEAM-001 | Replace collaborators through seams | Providers, stores, registries, and validators must be fakeable | Unit tests with fakes |
| TEST-FAIL-001 | Failure paths tested explicitly | Invalid JSON, schema failure, semantic rejection, and fallback must be tested | Negative tests |
| WF-RETRY-001 | Retry/cancellation semantics explicit | Worker attempt budgets, timeout behavior, and fallback must be explicit | Runtime state and tests |

**Current-System Analysis**
- The repo already has background task ownership via `BackgroundTaskRunner`, which gives a good operational seam for worker execution.
- The current agent run store and views show one pattern for explicit operational state, but the worker runtime should not reuse agent nouns such as turns or tool calls.
- The `soft-skills` `TypedLLMOutput` and marking provider pattern provides a strong precedent for splitting structural validation retries from semantic verification retries and final backup-provider selection.

**Options Considered**
- **Option A:** Model worker execution as one-step tasks with no persisted run/event history.
- **Option B:** Create a worker run model with explicit lifecycle state, result payload, events, retries, and cancellation.
- **Option C:** Piggyback on existing task-run snapshots alone and skip a worker-specific runtime store.

**Chosen Approach**
- Adopt Option B: create worker-specific runtime state and events, while still using the task runner as the execution owner.

**Decision Justification**
- Option B best satisfies `ERR-BG-001`, `OBS-BG-001`, and `WF-STATE-001` because worker execution becomes inspectable in its own terms rather than being hidden behind generic task snapshots.
- Option A would make failures too ephemeral and would undercut operational reviewability.
- Option C would preserve some lifecycle visibility, but task snapshots alone are too generic to carry worker-specific input/output, validation, and fallback state meaningfully.
- The worker runtime should store validated output directly as worker result state rather than as an “artifact,” because artifacts are intentionally being left conversational-only in this design.

**Execution Notes**
- Keep retry layers explicit:
  - provider transport retry at the provider edge for transient failures only
  - structured-output retry in the worker runtime
  - semantic retry above parsed validation, with optional backup provider/model on the final allowed attempt
- Keep timeout values explicit on worker invocation and preserve them in failure details.
- Keep local validation authoritative even when provider-side schema mode is used.

**Expected Evidence**
- **Tests:** unit tests for lifecycle state transitions, retry budget selection, corrective retry prompting, semantic retry, and backup-provider selection.
- **Runtime Evidence:** worker events show attempts, validation failures, fallback selection, and terminal outcome.
- **Review Checks:** no worker runtime code depends on tool bundles or `AgentTurn`-style response text semantics.

---

### Feature 4: Provider JSON Mode And Strictness Handling

**Description:** Add JSON generation support at the provider layer with provider-specific strict/non-strict handling and neutral response normalization.

**Affected Areas**
- OpenAI-compatible provider adapter
- JSON schema helper in `platform/llm/`
- worker runtime/provider call boundaries

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ERR-PROVIDER-001 | Keep provider failures classified and observable | JSON-mode request failures, strict-mode failures, timeout failures | Unit tests and structured errors |
| ERR-TRANS-001 | Preserve cause across boundaries | Provider JSON failures should retain underlying transport/context | Error translation tests |
| TEST-SMOKE-002 | Real-provider smoke coverage for critical provider path | Worker JSON path must be smoke-tested against a real provider | Real-provider smoke run |
| TEST-DET-001 | Stable assertions | Tests assert on JSON structure and lifecycle, not prose output | Test review |
| PRE-SCOPE-003 | Preserve adapter replaceability | Provider quirks isolated to adapter edge | Code review |

**Current-System Analysis**
- The current OpenAI-compatible adapter only supports chat text completions and cannot request provider-native JSON output.
- The `soft-skills` provider adapter uses `json_object` when no schema is provided and provider-specific `json_schema` handling when it is, including falling back to non-strict mode for providers with known limitations.
- That precedent fits the sprint’s stated preference: provider-side strictness is guidance, not correctness.

**Options Considered**
- **Option A:** Depend on prompt-only “return JSON” instructions and parse the resulting text.
- **Option B:** Add provider-native JSON mode with optional schema hints, and still validate locally.
- **Option C:** Require strict provider-side schema conformance and treat any strict-mode incompatibility as unsupported.

**Chosen Approach**
- Adopt Option B.

**Decision Justification**
- Option B gives the best balance of transport guidance and local correctness. It aligns with the `soft-skills` pattern and with the sprint’s design decision that local validation remains authoritative.
- Option A is weaker operationally and would make retries more expensive and less predictable.
- Option C would overfit the runtime to the best-behaving providers and would likely fail against “OpenAI-compatible” backends whose strict schema support is incomplete or inconsistent.

**Execution Notes**
- Default JSON output request should be `json_object` when no schema hint is provided.
- When a schema hint is present, the adapter chooses the strongest safe mode per provider.
- Keep strict/non-strict decisions entirely inside the adapter.

**Expected Evidence**
- **Tests:** adapter unit tests for `json_object`, strict `json_schema`, non-strict fallback, and provider error mapping.
- **Runtime Evidence:** provider call logs/events include provider/model/timeout metadata and distinguish transport failure from local validation failure.
- **Review Checks:** worker runtime does not contain provider-specific strictness branching.

---

### Feature 5: Worker Operational Surface And Stageflow Compatibility

**Description:** Expose workers through a narrow operational module and make worker execution callable from Stageflow subpipelines without over-formalising planner/fan-out.

**Affected Areas**
- `backend/src/hello_sales_backend/modules/worker_runs/`
- transport adapters for operational worker endpoints if added
- `backend/src/hello_sales_backend/platform/workflows/`

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| PRE-SCOPE-004 | Keep public APIs intentionally narrow | Worker endpoints must remain operational-only | Route/module review |
| ARCH-ENTRY-001 | Transport adapters stay thin | Routes call module service/facade only | Integration tests |
| OBS-DIAG-001 | Expose operator-relevant state | Worker run state/events should be inspectable | View/diagnostics tests |
| WF-BOUNDARY-001 | Workflow engine behind app-owned boundaries | Stageflow callers use app-owned worker runtime seams | Code review |
| WF-STATE-001 | Workflow outcomes explicit | Stageflow-driven worker outcomes still surface as worker run state | Integration tests |
| AGENT-EXPOSE-001 | Exposure flows through application modules | Worker exposure belongs in `modules/worker_runs/` | Module bootstrap review |

**Current-System Analysis**
- `modules/agent_runs/` already demonstrates the right architectural pattern for exposing runtime behavior through a module facade rather than transport reaching into platform code.
- Stageflow is already wrapped by app-owned workflow runtime helpers in `platform/workflows/`, which is the correct boundary for compatibility work.
- The `soft-skills` generation workers use Stageflow helper functions for worker subpipelines, but that pattern should be treated here as orchestration consumer behavior rather than as runtime identity.

**Options Considered**
- **Option A:** Expose worker state only indirectly through generic task diagnostics.
- **Option B:** Add a dedicated `modules/worker_runs/` operational surface and keep Stageflow compatibility behind worker runtime APIs.
- **Option C:** Formalise planner/fan-out abstractions in the generic worker runtime immediately.

**Chosen Approach**
- Adopt Option B and explicitly defer Option C.

**Decision Justification**
- Option B matches the module pattern already established by `agent_runs` and best satisfies `AGENT-EXPOSE-001` by analogy and `PRE-SCOPE-004` by keeping surfaces narrow and operational.
- Option A would not expose enough worker-specific state.
- Option C would violate the pre-brief discipline by codifying workflow assumptions before a real product use case exists.

**Execution Notes**
- Expose only what operators need: start, inspect, list events, cancel.
- If Stageflow compatibility requires correlation fields between parent and child runs, keep that as metadata rather than a generic planner model.

**Expected Evidence**
- **Tests:** integration tests for worker run views and events, plus Stageflow compatibility tests at the worker-runtime boundary.
- **Runtime Evidence:** worker state is inspectable independently of task-run snapshots and includes correlation metadata where available.
- **Review Checks:** no planner/synthesizer abstraction appears in generic worker runtime code.

## Deviations

| Requirement ID | Deviation | Reason | Risk | Disposition | Follow-up |
| --- | --- | --- | --- | --- | --- |
| None planned | No planned deviations at reasoning time | The sprint is scoped to generic runtime scaffolding and should be feasible within current contracts | If implementation reveals provider or persistence gaps, deviations must be recorded during execution | N/A | Update this table if any deviation becomes necessary |

## Cross-Cutting Reasoning

### Major Decision Summary

- **Sibling runtimes over a neutral substrate:** Driven by `AGENT-BOUNDARY-001`, `ARCH-SHARED-001`, and `PRE-SCOPE-003`, because worker and agent semantics differ materially while provider mechanics are still shared.
- **Local validation remains authoritative:** Driven by `ERR-PROVIDER-001`, `ERR-CORE-001`, and the provider variability already seen in OpenAI-compatible ecosystems.
- **Contract-first worker implementation:** Driven by the repo’s contract-led process and by the absence of a worker-specific contract today.
- **Stageflow compatibility without planner framework:** Driven by `WF-SCOPE-001` and `PRE-SCOPE-002`, which both discourage speculative orchestration abstraction.

### Trade-offs

- Extracting `platform/llm/` now adds refactor cost, but it prevents either runtime from becoming the accidental owner of provider abstractions.
- Persisting worker-specific runtime state adds infrastructure work beyond generic task snapshots, but that cost buys explicit inspectability and cleaner failure handling.
- Deferring planner abstractions keeps the sprint focused, but means future fan-out patterns may require another design pass once a concrete product workflow exists.

### Assumptions

- A narrow operational worker surface is acceptable pre-brief as long as it stays scaffold-oriented and not product-facing.
- One generic sample worker definition, if added, can remain obviously infrastructural and not commit the repo to a product domain.
- The existing task runner remains the right owner for background execution even if Stageflow is the orchestrator for some worker invocations.

### Dependencies

- **Current agent runtime and provider seams:** Existing files in `platform/agents/`, `modules/agent_runs/`, and `platform/providers/llm/` define the seams that must be preserved or extracted carefully.
- **Workflow wrapper:** Existing Stageflow integration in `platform/workflows/` should be reused rather than bypassed.
- **Reference implementation:** `soft-skills` files under `/home/antonioborgerees/df/soft-skills/backend/src/soft_skills_backend/` provide concrete patterns for JSON-mode providers, typed local validation, retry layering, and worker fan-out.

### Evidence Review Checklist

- [ ] Review can trace the worker/agent boundary decision back to explicit requirement IDs.
- [ ] Review can verify that provider JSON-mode support remains generic and that worker policy stays above the provider layer.
- [ ] Review can verify that worker lifecycle, retries, cancellation, and failure state are inspectable through stable operational surfaces.

## Phase Exit Criteria

- [ ] Tracker scope is fully covered
- [ ] Applicable requirements are mapped
- [ ] Ambiguous and non-applicable requirements are recorded where relevant
- [ ] Important decisions are explicitly justified
- [ ] Non-trivial alternatives are discussed
- [ ] Deviations, assumptions, risks, and unknowns are documented
- [ ] Expected evidence is defined

## Documentation Updates

- `ops/operational-contract/workers.md`: must be added to define the normative worker-runtime rules that this sprint will implement.
- `ops/operational-contract/README.md`: must list the new worker contract once it exists.
- `backend/docs/agent-runtime.md`: must be updated to clarify that agents are conversational-only and no longer the home of future structured worker behavior.
- `backend/docs/` worker/LLM runtime documentation: should explain the new `platform/llm/` substrate, the worker runtime boundary, and the retry/validation/fallback model.
