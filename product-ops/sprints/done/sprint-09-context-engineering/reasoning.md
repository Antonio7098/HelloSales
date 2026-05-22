# Sprint Reasoning: Context Engineering

> Project: HelloSales
> Sprint ID: sprint-09-context-engineering
> Created: 2026-04-24
> Output: `ops/sprints/done/sprint-09-context-engineering/reasoning.md`

## Overview

**Sprint:** Context Engineering
**Purpose:** Introduce a flexible, extendable context and prompt assembly system for the conversational agent runtime so context options can be swapped without coupling them to individual agent definitions.
**Tracker:** `ops/sprints/done/sprint-09-context-engineering/tracker.md`
**Depends On:** `ops/sprints/done/sprint-04-session-substrate-foundation/tracker.md`, `ops/sprints/done/sprint-08-workos-auth-foundation/tracker.md`

## Sprint Scope

Sprint 9 creates the context engineering layer for:
- `backend/src/hello_sales_backend/platform/agents/`
- `backend/src/hello_sales_backend/application/agents/`
- `backend/src/hello_sales_backend/platform/sessions/`

The target outcome is a provider-neutral and agent-agnostic context assembly system that can run the current basic behavior first, then add short-term memory, long-term memory, and conversation retrieval context without forcing each agent to hand-roll prompt/context code.

The sprint explicitly includes:
- extracting the current hard-coded context path into replaceable context strategies
- preserving the current basic session context behavior as the default
- adding stable contracts for context sources, prompt assembly options, budgets, provenance, and observability
- adding extension points for short-term memory, long-term memory, and future conversation RAG
- adding tests and docs that prove context profiles can be swapped without changing concrete agent definitions

The sprint explicitly excludes:
- designing vector stores, embeddings, chunking, indexing, ranking, or RAG primitives
- implementing a concrete long-term memory store beyond minimal contracts/fakes needed to prove the context seam
- changing provider-specific LLM APIs unless required to pass assembled messages through the existing provider port
- broad multi-agent orchestration

## Requirement Map

### Contract Coverage Reviewed For This Sprint

| Contract File | Area | Applicability | Why It Matters |
| --- | --- | --- | --- |
| `ops/operational-contract/README.md` | Contract index and process usage | Reviewed / Non-normative | Confirms the full contract set that reasoning must consider. |
| `ops/operational-contract/architecture.md` | Backend layering, dependency direction, composition | Applicable | The sprint adds a platform-owned runtime boundary and must keep agent definitions independent from concrete context sources. |
| `ops/operational-contract/errors.md` | Failure visibility, error shape, redaction | Applicable | Context source failure, missing profiles, malformed source output, and fallback policy must be explicit and redacted. |
| `ops/operational-contract/observability.md` | Events, correlation, diagnostics, alertable state | Applicable | Context profile/source selection and degraded context assembly need inspectable runtime signals. |
| `ops/operational-contract/testing.md` | Test seams, integration, smoke, failure coverage | Applicable | Context profiles and sources must be replaceable and verified deterministically. |
| `ops/operational-contract/workflows.md` | Workflow eligibility and orchestration semantics | Reviewed / Mostly non-applicable | The sprint should not introduce workflows for inline context assembly. Workflow constraints only matter as a guardrail. |
| `ops/operational-contract/llm.md` | LLM runtime boundaries, tools, lifecycle, prompt versioning | Applicable | Context assembly directly shapes conversational LLM calls and prompt provenance. |
| `ops/operational-contract/pre-brief-scope.md` | Scaffold-stage limits | Applicable | Context engineering is runtime scaffolding; product-specific memory semantics and broad public APIs must remain deferred. |
| `ops/operational-contract/frontend.md` | Frontend architecture | Reviewed / Non-applicable | The sprint is backend-runtime only and does not create or edit frontend code. |

### Requirement Index Used In This Sprint

| Requirement ID | Title | Area | Applicability | Why It Matters For This Sprint |
| --- | --- | --- | --- | --- |
| ARCH-CORE-001 | Module boundaries must remain explicit | Architecture | Applicable | Context behavior must have a clear platform/runtime owner and not leak into individual agent modules. |
| ARCH-CORE-002 | Dependency direction must point inward | Architecture | Applicable | Application agent definitions must not depend on concrete session stores, future memory stores, or retrieval adapters. |
| ARCH-LAYER-002 | Use cases depend on ports, not infra | Architecture | Applicable | Context sources for sessions, memory, and future retrieval need narrow contracts with fakeable implementations. |
| ARCH-MODULE-001 | Module public APIs must stay small and stable | Architecture | Applicable | Any application-agent surface changes should be minimal and durable. |
| ARCH-COMP-001 | Composition must happen through registrars | Architecture | Applicable | Context profiles and strategies should be wired through composition, not constructed ad hoc in the runtime. |
| ARCH-SHARED-001 | Shared and platform code must stay domain-neutral | Architecture | Applicable | The context engine is platform runtime infrastructure and must not encode product-specific agent behavior. |
| ERR-CORE-001 | No failure may disappear | Errors | Applicable | Context source and profile failures must be caller-visible or operator-visible according to source policy. |
| ERR-SHAPE-001 | Operational errors must preserve the canonical shape | Errors | Applicable | Missing profile and failed required-source errors need structured stable fields. |
| ERR-CODE-001 | Error codes must be stable and machine-usable | Errors | Applicable | Context failure codes need stable names such as `agent.context.profile_not_found` or `agent.context.source_failed`. |
| ERR-TRANS-001 | Error translation must preserve cause and context | Errors | Applicable | Source adapter failures must preserve original causes while adding run/source/profile metadata. |
| ERR-PROVIDER-001 | Provider failures must remain classified and observable | Errors | Applicable | If context assembly changes provider-facing prompts, provider errors still need prompt/context metadata. |
| ERR-DATA-001 | Persistence and data failures must be loud and distinct | Errors | Applicable | Session context source storage failures must not be confused with empty context. |
| ERR-REDACT-001 | Redaction must protect secrets without destroying diagnosis | Errors | Applicable | Context events must not leak private prompt, memory, retrieval, or tool payload text. |
| OBS-CORE-001 | Failures must produce structured operational signals | Observability | Applicable | Degraded or failed context assembly needs structured events. |
| OBS-CORR-001 | Correlation identifiers must survive subsystem boundaries | Observability | Applicable | Context assembly must preserve request, trace, run, turn, session, prompt, and profile identifiers. |
| OBS-DIAG-001 | Diagnostics surfaces must expose operator-relevant state | Observability | Applicable | Context profile/source state should be visible through events and possibly canonical diagnostics. |
| OBS-ALERT-001 | High-severity signals must be machine-usable for alerting | Observability | Applicable | Required-source failures and invalid profile configuration need stable codes and severity. |
| WF-SCOPE-001 | Workflows must be used only for real orchestration | Workflows | Non-Applicable | Inline context assembly is not workflow orchestration. |
| WF-BOUNDARY-001 | Workflow engines must stay behind app-owned boundaries | Workflows | Non-Applicable | The sprint does not add workflow-engine integration. |
| WF-STATE-001 | Workflow outcomes must be explicit and inspectable | Workflows | Non-Applicable | No workflow execution path is introduced. |
| WF-RETRY-001 | Retry and cancellation semantics must be explicit | Workflows | Non-Applicable | Context sources may have failure policy, but not workflow retry/cancellation semantics. |
| LLM-BOUNDARY-001 | Shared substrate, runtime mechanics, and mode-specific policy must stay separated | LLM | Applicable | Context assembly must stay separate from provider mechanics and concrete agent policy. |
| LLM-TOOL-001 | Tool execution boundaries must stay explicit and mode-scoped | LLM | Applicable | Tool replay and tool-result context must remain inspectable and not become hidden prompt stuffing. |
| LLM-IO-001 | Structured input and output boundaries must stay explicit when used | LLM | Non-Applicable | This sprint does not introduce structured-output execution. |
| LLM-LIFECYCLE-001 | Lifecycle controls must stay explicit and inspectable | LLM | Applicable | Context strategy selection and failures must be visible instead of silently falling back. |
| LLM-RUN-001 | Runs and events must be durable or inspectable | LLM | Applicable | Context profile, sources, and truncation decisions should be inspectable in run events or diagnostics. |
| LLM-PROMPT-001 | Prompts must be explicitly versioned and version propagation must stay observable | LLM | Applicable | Prompt assembly changes affect behavior and need versioned prompt/context metadata. |
| LLM-EXPOSE-001 | Operational exposure must flow through application modules | LLM | Applicable | Any new public context configuration or inspection surface must not expose platform internals directly. |
| LLM-OBS-001 | LLM runtime monitoring must reuse the canonical observability runtime | LLM | Applicable | Context assembly metrics/events should use existing runtime event and observability surfaces. |
| PRE-SCOPE-001 | Foundation work may proceed before the brief | Pre-Brief Scope | Applicable | Context engineering is generic runtime scaffolding. |
| PRE-SCOPE-002 | Product-specific commitments must wait for the brief | Pre-Brief Scope | Applicable | Long-term memory semantics and product-specific retrieval behavior must not be invented prematurely. |
| PRE-SCOPE-003 | Operational scaffolding should be favored over product assumptions | Pre-Brief Scope | Applicable | The sprint should build seams, profiles, and observability rather than business memory policy. |
| PRE-SCOPE-004 | Public APIs must remain intentionally narrow before the brief | Pre-Brief Scope | Applicable | Avoid broad public context-management APIs unless needed for runtime operation. |
| PRE-SCOPE-005 / PRE-SCOPE-006 | Frontend pre-brief limits | Pre-Brief Scope | Non-Applicable | No frontend work is planned. |
| FE-STRUCT-001 through FE-EXT-001 | Frontend structure, boundaries, state, API, tests, extensibility | Frontend | Non-Applicable | The sprint does not create or edit `frontend/`. |
| TEST-SEAM-001 | Collaborators must be replaceable through public seams | Testing | Applicable | Context sources and profiles are useful only if tests can swap them without private patching. |
| TEST-UNIT-001 | Business logic must have unit coverage | Testing | Applicable | Message ordering, budget selection, source precedence, and failure policy are deterministic logic. |
| TEST-INT-001 | Wiring and persistence changes must have integration coverage | Testing | Applicable | Runtime/composition wiring and session-source behavior must be exercised through realistic boundaries. |
| TEST-SMOKE-001 | Critical runtime paths must have smoke coverage | Testing | Applicable | The default context path is part of the primary conversational runtime. |
| TEST-SMOKE-002 | Critical external provider paths must have real-provider smoke coverage | Testing | Applicable | If real-provider prompt assembly behavior changes materially, run or explicitly defer provider smoke. |
| TEST-FAIL-001 | Failure paths must be tested explicitly | Testing | Applicable | Missing profiles, malformed source outputs, and context budget exhaustion need explicit behavior. |
| TEST-DET-001 | Tests must remain deterministic and non-brittle | Testing | Applicable | Context tests should assert message structure/provenance, not provider phrasing. |

### Applicable Requirements

- **ARCH-CORE-001 / ARCH-SHARED-001:** The new context engine belongs in platform runtime code because it is generic execution infrastructure, not a bounded product feature.
- **ARCH-CORE-002 / ARCH-LAYER-002:** Concrete context sources must depend on ports such as `SessionStorePort` or future memory/retrieval ports. Agent definitions must not import session persistence or retrieval implementations.
- **ARCH-COMP-001:** Context profiles, default strategy selection, and available source adapters must be assembled in the composition root.
- **ERR-CORE-001 / ERR-CODE-001 / ERR-TRANS-001:** Context source failures, malformed outputs, and missing profiles must use explicit stable codes and preserve causes rather than collapsing into empty context.
- **ERR-DATA-001:** Session-source storage failure must be treated differently from "no eligible context."
- **ERR-REDACT-001:** Context events and diagnostics must favor source/provenance metadata over raw private prompt, memory, retrieval, or tool payload text.
- **OBS-CORE-001 / OBS-CORR-001 / OBS-DIAG-001:** Context assembly must preserve correlation metadata and surface profile/source decisions through canonical runtime events or diagnostics.
- **LLM-BOUNDARY-001:** Prompt identity, context assembly, provider calls, and agent-specific behavior must remain distinct.
- **LLM-TOOL-001 / LLM-RUN-001:** Tool context replay must remain explicit and inspectable. It cannot be buried inside opaque summary text only.
- **LLM-PROMPT-001 / LLM-EXPOSE-001:** Context and prompt changes must produce stable metadata, and any operational exposure must flow through module facades rather than platform internals.
- **LLM-OBS-001:** Context assembly should emit canonical runtime events/fields for profile, source count, truncation, and failure decisions.
- **PRE-SCOPE-001 / PRE-SCOPE-003:** The sprint is valid pre-brief runtime scaffolding because it strengthens seams, replaceability, and observability.
- **PRE-SCOPE-002 / PRE-SCOPE-004:** The sprint must avoid product-specific memory behavior and avoid expanding public APIs beyond narrow operational needs.
- **TEST-SEAM-001:** A fake session source, fake memory source, and fake retrieval source must be enough to verify strategy composition.

### Non-Applicable Requirements

- **LLM-IO-001:** This sprint does not introduce a structured-output runtime path. If a future context source returns structured context, local validation should be covered by that source contract.
- **ERR-STARTUP-001 / OBS-HEALTH-001:** No required startup dependency or health/readiness behavior is introduced unless implementation adds mandatory context provider configuration. If that changes, reasoning must be updated.
- **ERR-HTTP-001:** No HTTP transport changes are planned. If request-level profile selection is added, transport error mapping must be included.
- **ERR-BG-001 / OBS-BG-001:** No new background task is planned; future memory consolidation is explicitly out of scope.
- **WF-SCOPE-001 / WF-BOUNDARY-001 / WF-STATE-001 / WF-RETRY-001:** No workflow is justified. Context assembly happens inline before the LLM call.
- **PRE-SCOPE-005 / PRE-SCOPE-006 and FE-STRUCT-001 through FE-EXT-001:** This sprint is backend-runtime focused and does not add frontend code, routes, state, API access, or UI surfaces.

### Ambiguous Or Conflicting Requirements

- **Agent-agnostic vs agent-specific prompt behavior:** Agent definitions still need a base behavior prompt, but context policy should not be coded separately per agent. Resolution: agents own their base prompt identity and tool catalog; the context engine owns source selection, ordering, memory, retrieval, and budget policy.
- **Long-term memory scope:** The user wants short and long-term memory options, but concrete durable memory design is not ready. Resolution: add contracts and fakes, not production memory storage, unless a minimal storage implementation naturally falls out of existing session persistence.
- **Conversation RAG:** The user wants RAG over this and past conversations, but RAG primitives are being done in parallel. Resolution: define only a consumer-side retrieval port that can accept externally produced ranked context later.

### Open Questions

- Whether context profile selection should be request-configurable at HTTP time or environment/config-only for the first release.
- Whether long-term memory should be scoped by actor, org, agent profile, or a combination. The contracts should support all three, but default implementation should avoid committing beyond actor/org metadata already present.
- Whether context provenance should be exposed through public session APIs or only internal run events/diagnostics initially.

## Current Research

**Research Status:** Completed on 2026-04-24.

### Sources Consulted

- [Anthropic, "Effective context engineering for AI agents"](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents): Current agent context guidance emphasizes treating context as finite, high-signal budget; using compaction, structured note-taking, and just-in-time retrieval.
- [OpenAI Agents SDK, Context management](https://openai.github.io/openai-agents-python/context/): Distinguishes local runtime context from model-visible context and lists instructions, input messages, tools, and retrieval/web search as model-visible context paths.
- [OpenAI Cookbook, short-term memory management with sessions](https://developers.openai.com/cookbook/examples/agents_sdk/session_memory): Frames trimming and compression as core short-term memory controls for long-running conversations.
- [LangChain, Context engineering in agents](https://docs.langchain.com/oss/python/langchain/context-engineering): Separates runtime context, state/short-term memory, store/long-term memory, and model context decisions.
- [LangChain, Memory overview](https://docs.langchain.com/oss/python/concepts/memory): Distinguishes short-term thread-scoped memory from long-term cross-conversation memory and notes semantic, episodic, and procedural memory categories.

### Relevant Current Guidance

- **Smallest high-signal context:** Context should be curated, not maximized. The sprint should add budgets and source precedence from the start.
- **Separate local context from model-visible context:** Auth, request IDs, dependencies, and stores are runtime context; only selected messages or source outputs should enter the LLM prompt.
- **Short-term memory as session state:** The current session summary plus recent turns maps cleanly to short-term memory and should become the default strategy.
- **Long-term memory as a separate store/source:** Cross-session memories should be recalled through a source contract with explicit scope and provenance, not mixed into session chronology.
- **Just-in-time retrieval:** Future conversation RAG should plug in as a context source that returns ranked relevant snippets or references. This sprint should not build its underlying retrieval primitives.
- **Compaction and structured notes:** Summaries and memory notes should be explicit source types with coverage/provenance rather than opaque concatenated prompt text.

### Options Or Guidance Rejected

- **Stuff all session history into the prompt:** Rejected because current guidance treats context as finite and performance-degrading when noisy.
- **Let each agent define its own memory and RAG behavior:** Rejected because it violates the user requirement for agent-agnostic switching and would duplicate context policy across agents.
- **Adopt a framework-specific memory stack now:** Rejected because the backend already has a provider-neutral runtime and session substrate. The sprint should preserve local boundaries and use framework guidance conceptually.
- **Design vector/RAG primitives in this sprint:** Rejected because that work is explicitly parallel and would overreach.

### Impact On Reasoning

- The default implementation should preserve current behavior but put it behind a named `basic` context profile.
- Context sources should emit provenance and estimated budget usage so review can see why a message entered the LLM call.
- Memory and retrieval should be source plugins, not agent prompt edits.
- Failure policy needs to be explicit: required context sources fail the turn; optional sources emit events and continue according to profile policy.

## Feature Analysis

### Feature 1: Context Assembly Contracts And Runtime Pipeline

**Description:** Add a platform-owned context assembly layer that turns run metadata, agent base messages, session state, and optional sources into final model-visible messages.

**Affected Areas**
- `backend/src/hello_sales_backend/platform/agents/runtime.py`
- `backend/src/hello_sales_backend/platform/agents/contracts.py`
- new context contracts under `backend/src/hello_sales_backend/platform/agents/`
- composition wiring under `backend/src/hello_sales_backend/platform/composition/`

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-SHARED-001 | Keep context logic platform-neutral | New context engine types | Import review and unit tests |
| ERR-CORE-001 | Source/profile failures do not disappear | Assembler failure policy | Failure-path tests |
| OBS-CORR-001 | Correlation survives context assembly | Build request/result metadata | Event assertions |
| LLM-BOUNDARY-001 | Keep context assembly separate from provider calls | `GenericAgentRuntime._run_agent_loop` delegates before `complete_with_tools` | Runtime tests |
| LLM-RUN-001 | Preserve inspectable assembly decisions | Context profile/source metadata in events | Integration tests |
| TEST-SEAM-001 | Sources can be swapped in tests | Context source protocols and fake implementations | Unit tests |

**Current-System Analysis**
- `GenericAgentRuntime._run_agent_loop` currently calls `definition.build_messages(turn.input_text)`, injects `_build_session_context_messages`, then appends replayed tool messages.
- `_build_session_context_messages` hard-codes completed summary injection, summary coverage filtering, `prior_items[-16:]`, and tool-result rendering.
- This is functional but not flexible: the runtime owns policy, source selection, ordering, and formatting all at once.

**Current Research Applied**
- OpenAI distinguishes runtime-local context from model-visible context, which supports a contract that receives run/session/auth metadata but only returns selected messages.
- Anthropic and LangChain both point toward context as a pipeline of selected sources rather than a monolithic prompt.

**Options Considered**
- **Option A:** Keep `_build_session_context_messages` and add flags for memory/RAG.
- **Option B:** Add a `ContextAssembler` with named profiles, ordered context sources, budget policy, and provenance.
- **Option C:** Move all context behavior into `AgentDefinition.build_messages`.

**Chosen Approach**
- Adopt Option B.

**Decision Justification**
- Option B is the only design that is both agent-agnostic and extendable.
- Option A would turn the runtime method into a conditional pile and make future memory/RAG additions brittle.
- Option C would duplicate context policy in every agent and violate the explicit user requirement.

**Execution Notes**
- Introduce request/result objects such as `AgentContextBuildRequest`, `AgentContextBuildResult`, `AgentContextProfile`, `AgentContextSource`, and `AgentContextSourceResult`.
- Include fields for `run_id`, `turn_id`, `session_id`, `profile_name`, `actor_id`, `org_id`, permissions, current input, base messages, and effective prompt ref.
- The assembler should return ordered `ChatMessage` items plus metadata: profile id/version, source ids, skipped sources, truncation decisions, and warnings.
- Keep tool-call replay explicit in the runtime unless it becomes a first-class source with the same inspectability.

**Expected Evidence**
- **Tests:** unit tests for source ordering, optional vs required source failure, and message placement around the system prompt.
- **Runtime Evidence:** run events include context profile, source count, and truncation/skipped-source metadata.
- **Review Checks:** concrete agent definitions do not import session stores, memory stores, or retrieval adapters.

---

### Feature 2: Default Basic Session Context Profile

**Description:** Preserve the current basic behavior as the default context profile while making it replaceable.

**Affected Areas**
- `backend/src/hello_sales_backend/platform/agents/runtime.py`
- `backend/src/hello_sales_backend/platform/sessions/`
- tests covering session-backed agent execution

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| LLM-LIFECYCLE-001 | Default behavior must not silently change | `basic` profile reproduces current summary/recent-item behavior | Regression tests |
| LLM-TOOL-001 | Tool result context remains explicit | Tool-result rendering source or runtime replay | Tests and event review |
| ERR-DATA-001 | Storage failure is distinct from empty context | Session source reads | Failure-path tests |
| ERR-REDACT-001 | Session/tool payloads are not leaked in metadata events | Context assembly events | Event payload review |
| TEST-SMOKE-001 | Primary runtime path remains healthy | Session-backed generic agent smoke | Smoke run or explicit deferral |

**Current-System Analysis**
- Existing behavior injects a completed summary as a system message, excludes items already covered by the summary, takes the last 16 prior user/assistant/tool-result items, and renders tool results as compact JSON system messages.
- The session substrate already stores `SessionItem` and `SessionSummary`, so the basic profile can be implemented without persistence changes.

**Current Research Applied**
- OpenAI Cookbook guidance supports trimming and compression as a first practical short-term memory layer.
- Anthropic guidance supports compaction plus recent context rather than unbounded transcript stuffing.

**Options Considered**
- **Option A:** Preserve exact behavior under `basic`.
- **Option B:** Change default to a more aggressive compaction-first profile immediately.
- **Option C:** Drop summaries and keep only recent messages.

**Chosen Approach**
- Adopt Option A.

**Decision Justification**
- The sprint is an architecture and extension sprint, so preserving behavior reduces regression risk.
- More aggressive context policy can be added as a second profile once the seam is proven.
- Existing summary coverage logic is already useful and maps to best-practice short-term memory.

**Execution Notes**
- Use profile id such as `basic-session-v1`.
- Keep the last-16 recent item limit as a named profile parameter, not an inline magic number.
- Preserve the existing summary warning language: historical context is not fresh evidence unless confirmed by current tool results.

**Expected Evidence**
- **Tests:** current session summary smoke and agent context tests still pass; add a direct unit test for `basic-session-v1` output ordering.
- **Runtime Evidence:** events show profile `basic-session-v1`.
- **Review Checks:** no observable default behavior change beyond new metadata.

---

### Feature 3: Short-Term And Long-Term Memory Extension Points

**Description:** Add contracts and profile slots for short-term memory variants and future long-term memory sources.

**Affected Areas**
- `backend/src/hello_sales_backend/platform/agents/`
- `backend/src/hello_sales_backend/platform/sessions/`
- `backend/src/hello_sales_backend/application/agents/contracts.py`

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-LAYER-002 | Memory stores are abstracted behind ports | Memory source contracts | Fake-source tests |
| PRE-SCOPE-002 | Product memory semantics are not invented prematurely | Long-term memory source scope | Review of source contract |
| LLM-PROMPT-001 | Memory-affecting prompts are versioned | Summary/memory prompt refs where used | Metadata tests |
| OBS-CORE-001 | Optional memory degradation is visible | Optional source skip events | Event tests |
| TEST-SEAM-001 | Memory behavior can be swapped | Fake long-term memory source | Unit tests |

**Current-System Analysis**
- The backend has session summaries but no durable long-term memory model.
- Auth context now carries actor/org metadata that can later scope memories.
- Agent definitions expose only prompt and tools, which is good for an agent-agnostic memory layer.

**Current Research Applied**
- LangChain separates state/short-term memory from store/long-term memory.
- The LangChain memory overview calls out semantic, episodic, and procedural memory; this sprint should make source categories possible without implementing all storage modes.

**Options Considered**
- **Option A:** Implement production long-term memory tables now.
- **Option B:** Add memory source contracts, fakes, profile config, and source categories now; defer storage.
- **Option C:** Ignore long-term memory until RAG primitives land.

**Chosen Approach**
- Adopt Option B.

**Decision Justification**
- Option B satisfies the need for smooth switching without prematurely designing memory storage.
- Option A risks committing to the wrong scope and persistence shape before product memory requirements are clear.
- Option C would leave the context system less extendable and force another runtime refactor soon.

**Execution Notes**
- Model memory as context source outputs with scope (`session`, `actor`, `org`, `agent`, or `global`), category (`semantic`, `episodic`, `procedural`, `summary`, `retrieval`), freshness metadata, and optional source refs.
- The sprint may add only no-op/fake long-term memory sources in production wiring unless a minimal in-memory source is needed for tests.
- Required vs optional memory sources must be profile-controlled.

**Expected Evidence**
- **Tests:** fake long-term memory source can be selected through a profile and contributes messages without changing an agent definition.
- **Runtime Evidence:** skipped optional memory source emits a warning event instead of failing silently.
- **Review Checks:** no vector or retrieval primitives are introduced under the memory label.

---

### Feature 4: Future Conversation RAG Integration Boundary

**Description:** Define only the consumer-side interface needed to ingest ranked conversation retrieval context from the parallel RAG work.

**Affected Areas**
- `backend/src/hello_sales_backend/platform/agents/`
- possible future adapter registration in composition

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-LAYER-002 | Retrieval is consumed through a narrow port | Retrieval context source interface | Contract tests |
| PRE-SCOPE-003 | Build integration scaffolding, not product retrieval behavior | Retrieval source port | Review for absence of RAG primitives |
| LLM-BOUNDARY-001 | Retrieval context stays separate from prompt/provider mechanics | Source output to assembler | Unit tests |
| ERR-CODE-001 | Retrieval source failure has stable codes | Fake failing retriever | Failure-path tests |
| TEST-SEAM-001 | Parallel RAG implementation can plug in later | Fake retriever source | Unit test with fake |

**Current-System Analysis**
- There is no conversation retrieval subsystem today.
- Sessions already persist conversation chronology, but this sprint should not decide how it is indexed or retrieved.

**Current Research Applied**
- Anthropic highlights just-in-time context and progressive disclosure, which argues for retrieval results that can be referenced and loaded selectively.
- OpenAI context guidance lists retrieval as one model-visible context path but does not require it to be embedded in the base prompt.

**Options Considered**
- **Option A:** Design RAG primitives now.
- **Option B:** Add a generic retrieval context source port that accepts query/run/session metadata and returns ranked context blocks or refs.
- **Option C:** Leave no retrieval seam and retrofit later.

**Chosen Approach**
- Adopt Option B.

**Decision Justification**
- Option B is the narrowest useful boundary for the parallel RAG work.
- Option A conflicts with explicit user direction.
- Option C would likely force another refactor of the same runtime method.

**Execution Notes**
- The port should not mention vector stores, embeddings, chunks, indexes, or specific ranking algorithms.
- Source results should carry `source_type`, `source_id`, `score` if provided, `text` or `ref`, and redaction/provenance metadata.
- The assembler should be able to include retrieved snippets or references according to profile budget rules.

**Expected Evidence**
- **Tests:** fake retriever source returns two ranked items and the assembler places them according to profile order and budget.
- **Runtime Evidence:** source metadata identifies retrieval as optional and records count/truncation.
- **Review Checks:** no embedding/indexing/chunking code exists in this sprint.

---

### Feature 5: Prompt Engineering Profiles And Agent-Agnostic Selection

**Description:** Make prompt/context options selectable without editing concrete agent prompts for each strategy.

**Affected Areas**
- `backend/src/hello_sales_backend/application/agents/contracts.py`
- `backend/src/hello_sales_backend/application/agents/definitions/*/prompts.py`
- `backend/src/hello_sales_backend/platform/llm/prompts.py`
- context profile config/composition

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| LLM-PROMPT-001 | Prompt-affecting options are versioned | Prompt/context profile metadata | Unit tests and run state |
| LLM-EXPOSE-001 | Operational exposure does not bypass modules | Any profile inspection/selection surface | Route/composition review if added |
| OBS-DIAG-001 | Profile/source state is inspectable | Run events or diagnostics | Integration tests |
| ARCH-MODULE-001 | Application-agent API remains small | Agent definition contract changes | Import/API review |
| TEST-DET-001 | Profile tests assert structure | Assembled message snapshots | Unit tests |

**Current-System Analysis**
- `AgentPromptDefinition` already has metadata and build functions, which is a good base.
- Current agent prompts include both behavior and schema context. Context strategy should not erase that, but it should own cross-cutting memory/retrieval/session context.

**Current Research Applied**
- Anthropic recommends clear prompts at the right altitude and canonical examples instead of sprawling prompt conditionals.
- OpenAI context guidance supports using instructions plus lower-priority input messages and tools, which maps to keeping agent base prompt separate from assembled contextual messages.

**Options Considered**
- **Option A:** Add prompt conditionals inside every agent prompt builder.
- **Option B:** Keep agent prompt metadata and add context profile metadata/version selected by runtime/config.
- **Option C:** Replace current prompt definitions entirely with one global prompt template.

**Chosen Approach**
- Adopt Option B.

**Decision Justification**
- Option B preserves existing prompt ownership and makes context switching agent-agnostic.
- Option A duplicates policy and would make new agents harder to onboard.
- Option C would flatten legitimate agent-specific behavior.

**Execution Notes**
- Keep `AgentPromptDefinition` focused on base behavior.
- Add context profile metadata such as `context_profile_id`, `context_profile_version`, and maybe `context_strategy_id`.
- Store or emit both prompt ref and context profile ref in events/logs.
- If HTTP selection is added, validate profile ids and permissions carefully; otherwise start with settings-based profile selection.

**Expected Evidence**
- **Tests:** same concrete agent definition can run with `basic-session-v1` and a fake memory-enabled profile.
- **Runtime Evidence:** prompt ref and context profile ref appear together in run events.
- **Review Checks:** agent prompt text is not expanded with memory/RAG-specific branching.

## Deviations

| Requirement ID | Deviation | Reason | Risk | Disposition | Follow-up |
| --- | --- | --- | --- | --- | --- |
| None planned | None | N/A | N/A | N/A | N/A |

## Cross-Cutting Reasoning

### Major Decision Summary

- **Context assembler over runtime flags:** Driven by ARCH-LAYER-002, LLM-BOUNDARY-001, and TEST-SEAM-001. A profile-based assembler keeps the runtime small and makes sources replaceable.
- **Preserve current behavior as `basic-session-v1`:** Driven by LLM-LIFECYCLE-001 and TEST-SMOKE-001. Sprint 9 should prove the seam before changing default behavior.
- **Contracts before storage for long-term memory:** Driven by ARCH-SHARED-001 and the user’s parallel RAG constraint. This avoids premature persistence and retrieval design.
- **RAG source port only:** Driven by explicit sprint exclusion and current best practice around just-in-time retrieval. The sprint creates a docking point, not the engine.

### Trade-offs

- The profile/source abstraction adds more types than a direct helper method, but it prevents the agent runtime from accumulating memory and retrieval conditionals.
- Deferring long-term memory storage means the sprint proves extensibility rather than shipping true persistent memory. That is acceptable because the storage and RAG details are not ready.
- Keeping the current default behavior means the first profile is conservative; more advanced context optimization comes after the seam is reviewable.

### Assumptions

- Context profile selection can start as configuration/composition unless the user explicitly needs per-request profile switching during implementation.
- The session substrate remains the authoritative short-term conversation state.
- Future RAG work can provide ranked snippets or references through a narrow retrieval source port.
- Long-term memory should be scoped with actor/org/session metadata already present but not committed to one scope only.

### Dependencies

- Sprint 4 session substrate supplies session chronology and summaries.
- Sprint 8 auth foundation supplies actor/org/permission metadata for source scoping.
- Parallel RAG work supplies retrieval primitives later; this sprint only defines the consumer boundary.

### Evidence Review Checklist

- Review can trace each context source and profile to explicit contracts.
- Review can verify default session-backed behavior is preserved.
- Review can see context profile/source metadata in tests or runtime events.
- Review can confirm no RAG primitives were introduced.
- Review can run unit/integration/smoke tests without real provider credentials.

## Phase Exit Criteria

- [ ] Tracker scope is fully covered
- [ ] Applicable requirements are mapped
- [ ] Ambiguous and non-applicable requirements are recorded
- [ ] Current context-engineering guidance was researched and tied to decisions
- [ ] Important decisions are explicitly justified
- [ ] Non-trivial alternatives are discussed
- [ ] Deviations, assumptions, risks, and unknowns are documented
- [ ] Expected evidence is defined

## Documentation Updates

- `backend/docs/agent-runtime.md`: document context profiles, source contracts, and default basic profile behavior.
- `backend/docs/runtime-overview.md`: document where context assembly sits relative to sessions, agent runtime, tools, and LLM providers.
- `backend/docs/codebase-map.md`: add new context-engineering files and ownership boundaries.
- Sprint tracker evidence: record tests, smoke status, and any real-provider smoke deferral.
