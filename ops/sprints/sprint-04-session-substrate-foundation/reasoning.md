# Sprint Reasoning: Session Substrate Foundation

> Project: HelloSales
> Sprint ID: sprint-04-session-substrate-foundation
> Output: `ops/sprints/sprint-04-session-substrate-foundation/reasoning.md`

## Overview

**Sprint:** Session Substrate Foundation
**Purpose:** Introduce a first-class session substrate that owns conversational chronology, session summaries, and trusted user/org context, then move the public conversational HTTP surface to a session-first model instead of exposing agent runs as the top-level conversation API.
**Tracker:** `ops/sprints/sprint-04-session-substrate-foundation/tracker.md`
**Depends On:** `ops/sprints/sprint-01-observability-foundation/tracker.md`, `ops/sprints/sprint-02-worker-runtime-foundation/tracker.md`

## Requirement Map

### Contract Coverage Reviewed For This Sprint

| Contract File | Area | Applicability | Why It Matters |
| --- | --- | --- | --- |
| `ops/operational-contract/architecture.md` | Layering and dependency direction | Applicable | The sprint adds a new bounded context and repositions agent runs as attached execution instead of conversation ownership. |
| `ops/operational-contract/errors.md` | Failure visibility and canonical shape | Applicable | Session summary generation, persistence, and API migration failures must remain explicit and inspectable. |
| `ops/operational-contract/observability.md` | Logging, correlation, diagnostics, background visibility | Applicable | Session summary generation is asynchronous and must have visible lifecycle state and correlation. |
| `ops/operational-contract/testing.md` | Verification expectations | Applicable | The sprint changes persistence, composition, transport, and background behavior. |
| `ops/operational-contract/workflows.md` | Workflow eligibility and boundary rules | Applicable | The sprint should avoid inventing workflow structure where ordinary services and task scheduling are sufficient. |
| `ops/operational-contract/llm.md` | LLM runtime boundaries, inspectability, prompt/version rules | Applicable | Session summary generation is LLM-backed and session state must remain durable, inspectable, and module-owned. |
| `ops/operational-contract/pre-brief-scope.md` | Pre-brief limits and safe scaffolding | Applicable | Session substrate and session-first operational APIs are valid foundation work; deep-research orchestration and concrete auth/tenancy commitments are not. |

### Requirement Index Used In This Sprint

| Requirement ID | Title | Area | Applicability | Why It Matters For This Sprint |
| --- | --- | --- | --- | --- |
| PRE-SCOPE-001 | Foundation work may proceed before the brief | Pre-Brief Scope | Applicable | Session substrate, session items, summaries, and narrow public APIs are valid scaffold-stage work. |
| PRE-SCOPE-002 | Product-specific commitments must wait for the brief | Pre-Brief Scope | Applicable | The sprint must not invent deep-research orchestration, business session semantics, or concrete auth/tenancy rules. |
| PRE-SCOPE-003 | Operational scaffolding should be favored over product assumptions | Pre-Brief Scope | Applicable | The design must stay generic and reusable across agent-backed and future non-agent session flows. |
| PRE-SCOPE-004 | Public APIs must remain intentionally narrow before the brief | Pre-Brief Scope | Applicable | The public surface should become session-first, but still narrow and operationally justified. |
| ARCH-CORE-001 | Module boundaries must remain explicit | Architecture | Applicable | `modules/sessions/` must become the public owner of session behavior. |
| ARCH-CORE-002 | Dependency direction must point inward | Architecture | Applicable | Session transport, module, runtime, and persistence layers must have clean ownership. |
| ARCH-LAYER-002 | Use cases depend on ports, not infra | Architecture | Applicable | Session services must depend on session ports and attached execution contracts, not SQLAlchemy directly. |
| ARCH-ENTRY-001 | Transport adapters must stay thin | Architecture | Applicable | New `/sessions` routes must remain adapter-thin. |
| ARCH-MODULE-001 | Module public APIs must stay small and stable | Architecture | Applicable | The session module should expose a focused service/facade and narrow views/commands only. |
| ARCH-COMP-001 | Composition must happen through registrars | Architecture | Applicable | Session assembly and agent attachment must be wired through the composition root. |
| ARCH-SHARED-001 | Shared and platform code must stay domain-neutral | Architecture | Applicable | Generic session storage/runtime helpers belong in platform code; business semantics do not. |
| ERR-CORE-001 | No failure may disappear | Errors | Applicable | Session creation, append, summary scheduling, and summary generation failures must remain explicit. |
| ERR-SHAPE-001 | Operational errors must preserve the canonical shape | Errors | Applicable | Session and summary failures must carry stable codes and context. |
| ERR-TRANS-001 | Error translation must preserve cause and context | Errors | Applicable | Summary generation crosses module, runtime, provider, and task boundaries. |
| ERR-HTTP-001 | Transport adapters must preserve the operational signal | Errors | Applicable | The new session-first routes must preserve structured failures. |
| ERR-BG-001 | Background work must end in explicit inspectable failure state | Errors | Applicable | Session summarization is asynchronous and must have owned task identity and terminal state. |
| ERR-PROVIDER-001 | Provider failures must remain classified and observable | Errors | Applicable | LLM-backed summary generation failures must not collapse into generic session failures. |
| ERR-DATA-001 | Persistence and data failures must be loud and distinct | Errors | Applicable | Session, item, and summary stores are new operational persistence surfaces. |
| OBS-CORE-001 | Failures must produce structured operational signals | Observability | Applicable | Summary jobs and session persistence failures need structured logs/events. |
| OBS-CORR-001 | Correlation identifiers must survive subsystem boundaries | Observability | Applicable | Session API calls, attached execution, and summary background tasks must preserve request and trace metadata. |
| OBS-DIAG-001 | Diagnostics surfaces must expose operator-relevant state | Observability | Applicable | Sessions and summary task state should be inspectable through canonical operational surfaces. |
| OBS-BG-001 | Background work must have visible terminal state | Observability | Applicable | Session summary generation must surface queued/running/completed/failed state. |
| OBS-ALERT-001 | High-severity signals must be machine-usable for alerting | Observability | Applicable | Summary generation and persistence failures should use stable codes and machine-usable fields. |
| TEST-SEAM-001 | Collaborators must be replaceable through public seams | Testing | Applicable | Session store, summary generator, context resolver, and executor attachment must be fakeable. |
| TEST-UNIT-001 | Business logic must have unit coverage | Testing | Applicable | Turn grouping, summary eligibility, and context assembly are deterministic logic. |
| TEST-INT-001 | Wiring and persistence changes must have integration coverage | Testing | Applicable | The sprint changes composition, routes, and persistence. |
| TEST-SMOKE-001 | Critical runtime paths must have smoke coverage | Testing | Applicable | Session creation, append, and session-backed conversational flow are critical runtime paths. |
| TEST-SMOKE-002 | Critical external provider paths must have real-provider smoke coverage | Testing | Applicable | Real-provider smoke should verify summary generation if it is a supported provider-backed path in this sprint. |
| TEST-FAIL-001 | Failure paths must be tested explicitly | Testing | Applicable | Summary generation and migration failure paths need explicit coverage. |
| TEST-DET-001 | Tests must remain deterministic and non-brittle | Testing | Applicable | Assertions should target session/item/state transitions, not model phrasing. |
| WF-SCOPE-001 | Workflows must be used only for real orchestration | Workflows | Applicable | The sprint should avoid inventing a workflow for session summary generation unless ordinary task scheduling proves insufficient. |
| WF-BOUNDARY-001 | Workflow engines must stay behind app-owned boundaries | Workflows | Applicable | If workflow runtime is touched at all, it must stay behind app-owned helpers. |
| LLM-BOUNDARY-001 | Shared substrate, runtime mechanics, and mode-specific policy must stay separated | LLM runtime | Applicable | Session summary generation should not collapse session logic into agent runtime internals. |
| LLM-TOOL-001 | Tool execution boundaries must stay explicit and mode-scoped | LLM runtime | Applicable | Session items must record tool calls/results explicitly without smuggling tool logic into session transport or hidden prompt state. |
| LLM-IO-001 | Structured input and output boundaries must stay explicit when used | LLM runtime | Applicable | Summary generation should use explicit structured output or authoritative local validation. |
| LLM-LIFECYCLE-001 | Lifecycle controls must stay explicit and inspectable | LLM runtime | Applicable | Summary queuing, retries, cancellation, and terminal state must be explicit. |
| LLM-RUN-001 | Runs and events must be durable or inspectable | LLM runtime | Applicable | Session items, summaries, and attached execution references must remain inspectable. |
| LLM-PROMPT-001 | Prompts must be explicitly versioned and version propagation must stay observable | LLM runtime | Applicable | Session summary prompt versions must be first-class and inspectable. |
| LLM-EXPOSE-001 | Operational exposure must flow through application modules | LLM runtime | Applicable | Session APIs must be exposed through `modules/sessions/`, not through platform runtime internals. |
| LLM-OBS-001 | LLM runtime monitoring must reuse the canonical observability runtime | LLM runtime | Applicable | Summary generation monitoring should reuse the existing observability runtime. |

### Applicable Requirements

- **PRE-SCOPE-001 / PRE-SCOPE-003:** A session substrate is valid scaffold-stage work because it is generic runtime and API foundation, not product logic.
- **PRE-SCOPE-002:** The sprint must stop short of designing deep research, planner behavior, or real auth/tenancy derivation. It can carry optional `actor_id`, `user_id`, and `org_id` fields, but not a concrete identity product model.
- **PRE-SCOPE-004:** The HTTP API may become session-first, but only in a narrow operational way. The sprint should not broaden the public surface into speculative collaboration or product domain APIs.
- **ARCH-CORE-001 / ARCH-MODULE-001:** Sessions must become their own bounded context with their own stable public module surface.
- **ARCH-CORE-002 / ARCH-LAYER-002 / ARCH-COMP-001:** Session transport, session service, session persistence, and attached execution seams must be separated cleanly and composed centrally.
- **ARCH-ENTRY-001:** Route handlers should only validate input, resolve context, call the session service, and map outputs.
- **ERR-CORE-001 / ERR-BG-001 / ERR-PROVIDER-001 / ERR-DATA-001:** Session summary background work and new persistence surfaces cannot hide failure in logs or implicit state.
- **OBS-CORE-001 / OBS-CORR-001 / OBS-BG-001 / OBS-DIAG-001:** Session summary jobs and attached execution state must be visible through existing observability and diagnostics seams.
- **WF-SCOPE-001:** The sprint should not introduce a workflow unless a real orchestration need emerges. A task-backed summary job is the simpler, more correct default.
- **LLM-BOUNDARY-001 / LLM-EXPOSE-001:** Session ownership belongs in a session module, not in the agent runtime or transport.
- **LLM-RUN-001 / LLM-PROMPT-001:** Session summary prompt identity and summary lifecycle state must be durable and inspectable.

### Non-Applicable Requirements

- **OBS-HEALTH-001:** The sprint does not change health/readiness truth directly, though summary provider failures must remain visible as operational degradation where appropriate.
- **WF-BOUNDARY-001 as a primary driver:** No new workflow is justified by the intended sprint scope; workflow boundary rules matter mainly as a guard against unnecessary orchestration.

### Ambiguous Or Conflicting Requirements

- **PRE-SCOPE-002 and user/org context:** The sprint should support trusted user/org context as a substrate concern, but concrete auth and tenancy derivation are still pre-brief unknowns. The safe interpretation is to support optional identifiers and replaceable context resolvers rather than concrete auth policy.
- **PRE-SCOPE-004 and public API replacement:** Replacing `/agent-runs` with `/sessions` is a public-surface change, but it narrows and clarifies the API instead of broadening it. The safe interpretation is that “session-first” is allowed because it improves foundational correctness without adding speculative product breadth.

### Open Questions

- None remaining at reasoning completion. The main ambiguity around user/org derivation is resolved by keeping the resolver optional and replaceable.

### Resolved Decisions

- **Conversation ownership:** `AgentRun` will no longer be treated as the conversation root. `Session` becomes the durable conversation container.
- **Public API stance:** The public conversational API becomes session-first in this sprint; `/agent-runs` is no longer the public top-level conversation surface.
- **Executor stance:** The sprint defines a generic attached-execution seam so an agent can plug into a session, but it does not design deep research or broader pipeline semantics.
- **Summary cadence stance:** Session summarization cadence is configurable by settings and not hard-coded to eight turns.
- **Summary runtime stance:** Summary generation uses background task ownership, not a new workflow, unless real orchestration need emerges during implementation.
- **Prompt stance:** Session summary prompts are versioned separately from conversational response prompts.

## Feature Analysis

### Feature 1: First-Class Session Substrate

**Description:** Add a neutral session substrate that owns session identity, append-only session items, trusted user/org context references, and session summary state.

**Affected Areas**
- `backend/src/hello_sales_backend/platform/sessions/`
- `backend/src/hello_sales_backend/modules/sessions/`
- `backend/src/hello_sales_backend/platform/db/models.py`
- `backend/src/hello_sales_backend/platform/db/repositories.py`
- `backend/alembic/versions/`
- `backend/src/hello_sales_backend/platform/composition/app_container.py`

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-CORE-001 | Session behavior must have explicit ownership | `modules/sessions/` and `platform/sessions/` split | File ownership and import review |
| ARCH-LAYER-002 | Session services depend on ports, not SQLAlchemy | session service constructor and persistence ports | Unit/integration tests |
| ARCH-COMP-001 | New substrate is assembled through composition | container wiring and module bootstrap | Integration tests |
| PRE-SCOPE-003 | Keep the substrate reusable and executor-neutral | neutral models and item types | Review of names and boundaries |
| ERR-DATA-001 | New persistence surfaces fail loudly | session/item/summary persistence behavior | Integration and failure-path tests |
| LLM-RUN-001 | Session items and summaries remain inspectable | durable store and operational views | Route and persistence tests |

**Current-System Analysis**
- The backend currently treats `AgentRun` and `AgentTurn` as the durable conversation thread, which couples conversational chronology to one executor family.
- Current public routes are mounted at `/agent-runs` and are documented as the conversation API.
- The store already persists tool calls and ordered events, which is useful prior art, but the ownership boundary is agent-specific rather than session-specific.
- What must remain true is that durable chronology, ordered inspection, and explicit lifecycle state stay first-class.

**Options Considered**
- **Option A:** Extend `AgentRun` with more fields and treat it as the de facto session object.
- **Option B:** Add a session substrate as a separate bounded context and let executors attach to it.
- **Option C:** Defer session substrate until a broader multi-executor design exists.

**Chosen Approach**
- Adopt Option B. Create a first-class session substrate with neutral session, session-item, and session-summary models and ports.

**Decision Justification**
- Option B matches the architectural objection directly: sessions should be reusable across executor families and should not inherit agent-specific concepts like turns, approvals, or response text as their core identity.
- Option A would preserve the existing coupling and make a later multi-executor refactor harder.
- Option C would leave the system on the wrong conceptual boundary and preserve a misleading public API.
- The substrate should stay intentionally narrow: session identity, ordered items, summary state, and trusted context references are in scope; deep-research semantics are not.

**Execution Notes**
- Use neutral item types such as `user_message`, `assistant_message`, `tool_call`, `tool_result`, `summary`, `artifact_ref`, and `system_note`.
- Support optional `actor_id`, `user_id`, and `org_id` fields and replaceable context-resolution ports without committing to a concrete auth product model.
- Keep item ordering and inspectability explicit and append-only.

**Expected Evidence**
- **Tests:** unit coverage for item ordering and summary-coverage logic; integration coverage for persistence round-trips.
- **Runtime Evidence:** new diagnostics or operational views can inspect session, items, and summary metadata.
- **Review Checks:** session models and services do not import agent internals or SQLAlchemy adapters directly.

---

### Feature 2: Session-First Public Conversational API

**Description:** Replace the current public conversational API root with session-first routes so conversations are created, appended, inspected, and observed through `/sessions` rather than `/agent-runs`.

**Affected Areas**
- `backend/src/hello_sales_backend/entrypoints/http/router.py`
- `backend/src/hello_sales_backend/entrypoints/http/routes/`
- `backend/src/hello_sales_backend/modules/sessions/use_cases/`
- `backend/docs/api-and-runtime-surfaces.md`
- `backend/docs/runtime-overview.md`

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| PRE-SCOPE-004 | Public surface should be narrow and scaffold-oriented | `/sessions` route shape and scope | Route review and docs |
| ARCH-ENTRY-001 | Routes stay thin | route handlers and dependencies | Integration tests and code review |
| ARCH-MODULE-001 | Public module API stays small | session service, commands, and views only | Module export review |
| ERR-HTTP-001 | Structured failure signals survive transport | session route errors | Negative integration tests |
| LLM-EXPOSE-001 | Exposure flows through application modules | session routes call `modules/sessions` facade | Composition and route review |

**Current-System Analysis**
- Today the top-level router mounts `/agent-runs`, `/worker-runs`, `/jobs`, and `/system`.
- `/agent-runs` is currently both the public conversation API and the executor runtime API, which is the coupling this sprint is correcting.
- What must remain true is that conversational append/inspect/event behavior remains available, but owned by sessions rather than by agent runs.

**Options Considered**
- **Option A:** Add `/sessions` while keeping `/agent-runs` as a peer public API.
- **Option B:** Make `/sessions` the public conversational surface and remove `/agent-runs` as the public top-level conversation API.
- **Option C:** Keep the API unchanged and only refactor internals.

**Chosen Approach**
- Adopt Option B. The public conversational API becomes session-first in this sprint rather than keeping dual public roots.

**Decision Justification**
- Option B is the only approach that satisfies the “no half measures” constraint. Dual public roots would preserve conceptual ambiguity and force clients to choose between competing conversation nouns.
- Option C would leave the architecture and docs lying about the real ownership boundary.
- The session-first surface remains narrow and operationally justified because it only covers creation, append, inspection, event observation, and attached execution entrypoints required for conversation handling.

**Execution Notes**
- Session creation and continuation should route through `/sessions`.
- If a conversational agent is the attached executor used to answer a user message, that should happen behind the session facade rather than by exposing `/agent-runs` as the public root.
- `worker-runs` may remain for non-conversational structured execution until a session-backed worker use case exists; this sprint is not required to redesign those paths.

**Expected Evidence**
- **Tests:** integration tests for session create/append/get/events routes and error mapping.
- **Runtime Evidence:** route behavior exposes session ids, ordered items, and summary metadata where applicable.
- **Review Checks:** `/agent-runs` is no longer treated as the public conversation root in router docs and runtime docs.

---

### Feature 3: Configurable X-Turn Session Summarization

**Description:** Add background session summarization that triggers after a configurable number of eligible session turns rather than a hard-coded threshold.

**Affected Areas**
- `backend/src/hello_sales_backend/platform/config/settings.py`
- `backend/src/hello_sales_backend/modules/sessions/use_cases/`
- `backend/src/hello_sales_backend/platform/sessions/`
- `backend/src/hello_sales_backend/platform/tasks/runner.py`
- provider-backed summary prompt definitions and runtime helpers

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ERR-BG-001 | Summary jobs need explicit terminal state | task ids, status, and failure detail | Failure-path and integration tests |
| OBS-BG-001 | Background visibility is mandatory | summary task snapshots and events | Diagnostics and tests |
| LLM-LIFECYCLE-001 | Summary lifecycle must be explicit | queued/running/completed/failed semantics | Run state and event tests |
| LLM-PROMPT-001 | Summary prompt must be versioned | prompt metadata and stored prompt refs | Unit and persistence tests |
| LLM-IO-001 | Summary output must validate locally if structured | structured summary parsing or schema validation | Unit tests |
| TEST-FAIL-001 | Failure paths tested explicitly | provider error, invalid output, persistence failure | Negative tests |

**Current-System Analysis**
- The backend already has a background task runner with owned task ids, snapshots, and failure capture.
- There is no current session summary concept, and the generic agent prompt path is currently driven by raw input plus tool context.
- The current code already versions prompts and emits observability for LLM-backed runtime paths, which the summary path should reuse rather than reimplement.

**Options Considered**
- **Option A:** Hard-code eight turns and summarize inline during the conversational request path.
- **Option B:** Add configurable turn cadence and schedule summary generation as background work.
- **Option C:** Defer summary generation entirely until broader multi-executor session usage exists.

**Chosen Approach**
- Adopt Option B. Summary cadence is configurable through settings and summary generation is owned by background task execution.

**Decision Justification**
- Option B satisfies the explicit request and best aligns with the existing background-task and observability contracts.
- Option A would hard-code product behavior prematurely and make request latency and failure handling worse.
- Option C would leave the session substrate without the compaction mechanism that justifies it operationally.
- The cadence should be framed as “eligible session turns,” not as a hidden agent-specific counter.

**Execution Notes**
- The setting should be a positive integer such as `session_summary_turn_interval`.
- Summary eligibility should be defined in session terms and remain deterministic.
- Summary prompts must have their own prompt id/version and be persisted alongside summary state.
- If provider-backed summary generation is a supported path in this sprint, add real-provider smoke coverage or record an explicit justified deferral.

**Expected Evidence**
- **Tests:** unit tests for summary eligibility and prompt version propagation; integration tests for task scheduling and state transitions.
- **Runtime Evidence:** summary events and task snapshots show queued/running/completed/failed states with stable codes.
- **Review Checks:** no inline request-path summarization, no hard-coded eight-turn constant in logic, and summary prompt/version fields are inspectable.

---

### Feature 4: Agent As Attached Execution, Not Session Owner

**Description:** Reframe the conversational agent as an attached execution path that reads from and writes to a session instead of owning the conversation root itself.

**Affected Areas**
- `backend/src/hello_sales_backend/platform/agents/`
- `backend/src/hello_sales_backend/modules/agent_runs/`
- `backend/src/hello_sales_backend/modules/sessions/`
- composition wiring and runtime docs

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-CORE-002 | Ownership and dependency direction stay clear | session-to-agent attachment seam | Code review and integration tests |
| LLM-BOUNDARY-001 | Session logic and agent runtime mechanics stay separated | agent runtime no longer owns conversation identity | Package review |
| LLM-TOOL-001 | Tool calls remain explicit and inspectable | tool call/result session items and runtime records | Tests and operational views |
| LLM-RUN-001 | Execution remains inspectable | agent execution state still durable | Integration tests |

**Current-System Analysis**
- The current agent runtime persists runs, turns, tool calls, and events directly and is exposed through `modules/agent_runs/`.
- That shape is appropriate for executor lifecycle but too coupled to serve as the general session substrate.
- What must remain true is that agent execution state, tool approval behavior, and operational inspectability do not regress during the boundary move.

**Options Considered**
- **Option A:** Keep agent-owned turn history and mirror it into sessions.
- **Option B:** Make session chronology canonical and let agent execution attach to it.
- **Option C:** Postpone the boundary change and only add standalone sessions beside agent runs.

**Chosen Approach**
- Adopt Option B. Session chronology becomes canonical and agent execution becomes attached execution.

**Decision Justification**
- Option B enforces the desired ownership boundary and avoids maintaining two canonical transcripts.
- Option A creates synchronization risk and preserves confusion.
- Option C leaves the central conceptual problem unresolved and undercuts the session-first public API stance.
- The sprint should not redesign worker or deep-research execution semantics; it only needs the generic attached-execution seam and the conversational-agent adaptation required for the public API move.

**Execution Notes**
- Preserve inspectable agent execution state and tool-call durability.
- Do not design deep-research execution structure in this sprint.
- If module names remain temporarily agent-specific internally, runtime docs must still make clear that session is the public conversation owner.

**Expected Evidence**
- **Tests:** integration tests for a session-backed conversational flow using the current agent.
- **Runtime Evidence:** agent execution still emits inspectable lifecycle state, while the session owns chronology.
- **Review Checks:** there is no dual canonical transcript and no public route that treats agent run id as the conversation id.

## Deviations

| Requirement ID | Deviation | Reason | Risk | Disposition | Follow-up |
| --- | --- | --- | --- | --- | --- |
| PRE-SCOPE-002 | Concrete auth and tenancy derivation remains unresolved in this sprint | The brief does not yet justify a concrete identity model | User/org context wiring could need later adjustment | Temporary | Follow up once auth and tenancy constraints are known |

## Cross-Cutting Reasoning

### Major Decision Summary

- **Session becomes the conversation root:** `ARCH-CORE-001`, `ARCH-CORE-002`, `LLM-BOUNDARY-001`, and `LLM-EXPOSE-001` all point toward a new `sessions` module rather than further extending `agent_runs`.
- **Public API becomes session-first without a dual-root compatibility period:** `PRE-SCOPE-004` allows a narrow foundational API shift, and the explicit “no half measures” constraint rules out parallel public roots.
- **Summary cadence is configurable, not hard-coded:** this best fits `PRE-SCOPE-002`, `ERR-BG-001`, `LLM-LIFECYCLE-001`, and the desire to keep the substrate reusable.
- **No deep-research design in this sprint:** `PRE-SCOPE-002` and `WF-SCOPE-001` both argue against speculative multi-executor orchestration design here.

### Trade-offs

- Moving the public conversational API to `/sessions` now is a larger migration than a compatibility path would be, but it prevents a second round of conceptual churn and client ambiguity.
- Defining only the session substrate and agent attachment seam leaves broader multi-executor orchestration for later, but that is the correct boundary for pre-brief foundation work.
- Supporting user/org context as optional identifiers and replaceable resolvers preserves extensibility, but it deliberately avoids final auth semantics in this sprint.

### Assumptions

- A session substrate is foundational infrastructure rather than a product-specific commitment.
- The current generic conversational agent remains the attached executor used for session-backed conversational responses in this sprint.
- Session summary generation is a supported provider-backed runtime path if implemented with a real provider in normal operation.
- The existing background task runner is sufficient for summary job ownership and no new workflow layer is required.

### Dependencies

- `ops/sprints/sprint-01-observability-foundation/`: provides the telemetry and background-task visibility this sprint will reuse.
- `ops/sprints/sprint-02-worker-runtime-foundation/`: establishes the sibling-runtime pattern and prompt/version expectations this sprint extends.
- `backend/docs/api-and-runtime-surfaces.md`: will need to be updated so the documented public API matches the session-first design.
- `backend/docs/runtime-overview.md`: will need to be updated so session ownership and attached execution are explained correctly.

### Evidence Review Checklist

- [x] Review can trace every feature decision back to explicit requirement IDs
- [x] Review can verify the planned tests and runtime evidence exist
- [x] Review can identify planned deviations and follow-up scope

## Phase Exit Criteria

- [x] Tracker scope is fully covered
- [x] Applicable requirements are mapped
- [x] Ambiguous and non-applicable requirements are recorded where relevant
- [x] Important decisions are explicitly justified
- [x] Non-trivial alternatives are discussed
- [x] Deviations, assumptions, risks, and unknowns are documented
- [x] Expected evidence is defined

## Documentation Updates

- `backend/docs/api-and-runtime-surfaces.md`: must document `/sessions` as the public conversational API root and remove `agent-runs` as the canonical conversation surface.
- `backend/docs/runtime-overview.md`: must explain that sessions own chronology while executors attach to sessions.
- `backend/docs/agent-runtime.md`: must be updated so agent runtime is described as attached conversational execution rather than the conversation root.
- `backend/docs/codebase-map.md`: must add `modules/sessions/` and `platform/sessions/` ownership.
