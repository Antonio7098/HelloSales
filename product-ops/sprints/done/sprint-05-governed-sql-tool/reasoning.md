# Sprint Reasoning: Governed SQL Tool

> Project: HelloSales
> Sprint ID: sprint-05-governed-sql-tool
> Output: `ops/sprints/sprint-05-governed-sql-tool/reasoning.md`

## Overview

**Sprint:** Governed SQL Tool
**Purpose:** Add one governed agent tool that lets the generic agent answer analytics questions by executing validated read-only SQL against curated analytics views, while keeping the capability schema-agnostic, operationally inspectable, and safe for scaffold-stage use.
**Tracker:** `ops/sprints/sprint-05-governed-sql-tool/tracker.md`
**Depends On:** `ops/sprints/done/sprint-01-observability-foundation/tracker.md`, `ops/sprints/done/sprint-02-worker-runtime-foundation/tracker.md`, `ops/sprints/done/sprint-04-session-substrate-foundation/tracker.md`

This sprint does not introduce a broad “database access” surface.
It introduces one agent tool that accepts SQL within a governed boundary.
The capability is intentionally narrower than arbitrary SQL:
- read-only only
- one dialect initially
- curated catalog/views only
- bounded result shape
- explicit redaction and truncation
- explicit operational metadata

This sprint also does not redesign the agent runtime again.
The native tool-calling loop is already present in `platform/agents/runtime.py` and `platform/llm/providers/openai_compatible.py`.
Sprint 5 builds on that runtime by adding one governed tool and the module-owned services behind it.

## Requirement Map

### Contract Coverage Reviewed For This Sprint

| Contract File | Area | Applicability | Why It Matters |
| --- | --- | --- | --- |
| `ops/operational-contract/architecture.md` | Layering, ownership, composition | Applicable | The sprint adds a new bounded context and must not bury business or policy logic in `platform/`. |
| `ops/operational-contract/errors.md` | Error visibility, provider/data classification, redaction | Applicable | SQL validation, execution, catalog lookup, and redaction failures must remain explicit and machine-usable. |
| `ops/operational-contract/observability.md` | Correlation, diagnostics, operator visibility | Applicable | Query execution introduces new failure and runtime visibility needs. |
| `ops/operational-contract/testing.md` | Unit, integration, smoke, failure-path coverage | Applicable | The sprint changes runtime behavior, persistence-adjacent logic, and provider-backed execution. |
| `ops/operational-contract/workflows.md` | Workflow eligibility and retry/cancellation semantics | Applicable | The sprint must avoid inventing a workflow for ordinary tool execution. |
| `ops/operational-contract/llm.md` | Tool boundaries, lifecycle inspectability, prompt/version propagation, operational exposure | Applicable | This is an LLM-backed conversational tool path with approvals, provider execution, and durable tool state. |
| `ops/operational-contract/pre-brief-scope.md` | Safe scaffold-stage work and non-goals | Applicable | The sprint must stay generic and avoid product-specific analytics commitments. |

### Requirement Index Used In This Sprint

| Requirement ID | Title | Area | Applicability | Why It Matters For This Sprint |
| --- | --- | --- | --- | --- |
| PRE-SCOPE-001 | Foundation work may proceed before the brief | Pre-Brief Scope | Applicable | A governed query capability and semantic catalog are valid runtime scaffolding. |
| PRE-SCOPE-002 | Product-specific commitments must wait for the brief | Pre-Brief Scope | Applicable | The sprint must avoid product-specific CRM semantics, broad lead export workflows, or guessed analytics entities beyond a generic catalog format. |
| PRE-SCOPE-003 | Operational scaffolding should be favored over product assumptions | Pre-Brief Scope | Applicable | The solution should prefer replaceable catalog, validator, executor, and redaction seams over hard-coded business logic. |
| PRE-SCOPE-004 | Public APIs must remain intentionally narrow before the brief | Pre-Brief Scope | Applicable | The sprint should add one narrow agent tool rather than a broad family of analytics APIs. |
| ARCH-CORE-001 | Module boundaries must remain explicit | Architecture | Applicable | The governed SQL capability needs a bounded context of its own rather than scattered helper logic. |
| ARCH-CORE-002 | Dependency direction must point inward | Architecture | Applicable | Tool, module, validator, executor, and persistence-facing seams must follow existing layering. |
| ARCH-LAYER-002 | Use cases depend on ports, not infra | Architecture | Applicable | The analytics service should depend on catalog, validation, executor, and redaction ports. |
| ARCH-ENTRY-001 | Transport adapters must stay thin | Architecture | Non-Applicable | No new HTTP route is introduced in this sprint. |
| ARCH-MODULE-001 | Module public APIs must stay small and stable | Architecture | Applicable | `modules/analytics_query/` should export a narrow service and views/commands only. |
| ARCH-COMP-001 | Composition must happen through registrars | Architecture | Applicable | The new module and tool must be assembled through module bootstrap and the composition root. |
| ARCH-SHARED-001 | Shared and platform code must stay domain-neutral | Architecture | Applicable | Catalog- and query-specific policy must not be buried in `shared/` or generic platform code. |
| ERR-CORE-001 | No failure may disappear | Errors | Applicable | Unsafe SQL, forbidden relations, redaction failures, executor failures, and approval boundaries must stay explicit. |
| ERR-SHAPE-001 | Operational errors must preserve the canonical shape | Errors | Applicable | Query failures need stable codes, categories, details, operation, component, and preserved cause. |
| ERR-CODE-001 | Error codes must be stable and machine-usable | Errors | Applicable | Query validation, policy, provider, and data failures need precise codes. |
| ERR-TRANS-001 | Error translation must preserve cause and context | Errors | Applicable | SQL parser, executor, provider, and catalog failures cross multiple boundaries. |
| ERR-HTTP-001 | Transport adapters must preserve the operational signal | Errors | Applicable | Session-backed conversational APIs will surface tool failures indirectly and must preserve structured error meaning. |
| ERR-PROVIDER-001 | Provider failures must remain classified and observable | Errors | Applicable | Provider-generated bad tool arguments and provider request failures remain part of the agent path. |
| ERR-DATA-001 | Persistence and data failures must be loud and distinct | Errors | Applicable | Catalog loading, tool-call state, and SQL execution failures against the data store must remain distinct. |
| ERR-REDACT-001 | Redaction must protect secrets without destroying diagnosis | Errors | Applicable | Query results and error details must be redacted without hiding which policy failed. |
| OBS-CORE-001 | Failures must produce structured operational signals | Observability | Applicable | Query policy and execution failures must appear in events/logs/diagnostics. |
| OBS-CORR-001 | Correlation identifiers must survive subsystem boundaries | Observability | Applicable | Query planning, validation, execution, and agent tool state must preserve request and trace metadata. |
| OBS-DIAG-001 | Diagnostics surfaces must expose operator-relevant state | Observability | Applicable | Query metadata and failures should be inspectable through existing diagnostics paths where appropriate. |
| OBS-ALERT-001 | High-severity signals must be machine-usable for alerting | Observability | Applicable | Repeated query failures should be distinguishable by stable code. |
| TEST-SEAM-001 | Collaborators must be replaceable through public seams | Testing | Applicable | Catalog, validator, executor, and redactor must be fakeable. |
| TEST-UNIT-001 | Business logic must have unit coverage | Testing | Applicable | Risk classification, policy, schema normalization, and output shaping are deterministic logic. |
| TEST-INT-001 | Wiring and persistence changes must have integration coverage | Testing | Applicable | Module wiring, catalog loading, and execution behavior need integration coverage. |
| TEST-SMOKE-001 | Critical runtime paths must have smoke coverage | Testing | Applicable | The agent tool loop with the SQL tool is a critical runtime path. |
| TEST-SMOKE-002 | Critical external provider paths must have real-provider smoke coverage | Testing | Applicable | The provider-backed agent runtime path should prove the SQL tool loop at the supported boundary. |
| TEST-FAIL-001 | Failure paths must be tested explicitly | Testing | Applicable | Unsafe SQL, forbidden views, timeout, truncation, and redaction failures need explicit tests. |
| TEST-DET-001 | Tests must remain deterministic and non-brittle | Testing | Applicable | Coverage should assert lifecycle and structure, not wording. |
| WF-SCOPE-001 | Workflows must be used only for real orchestration | Workflows | Applicable | Tool execution should remain an ordinary service/tool path, not a workflow. |
| WF-BOUNDARY-001 | Workflow engines must stay behind app-owned boundaries | Workflows | Applicable | The sprint must not leak workflow runtime into analytics query services. |
| LLM-BOUNDARY-001 | Shared substrate, runtime mechanics, and mode-specific policy must stay separated | LLM Runtime | Applicable | SQL governance belongs in a module and tool service, not in shared provider code. |
| LLM-TOOL-001 | Tool execution boundaries must stay explicit and mode-scoped | LLM Runtime | Applicable | SQL execution must remain an explicit conversational tool with persisted tool-call lifecycle. |
| LLM-LIFECYCLE-001 | Lifecycle controls must stay explicit and inspectable | LLM Runtime | Applicable | Approval, rejection, failure, and completion semantics must remain explicit. |
| LLM-RUN-001 | Runs and events must be durable or inspectable | LLM Runtime | Applicable | Query tool calls, results, and failures must remain inspectable through run/turn/tool-call state and session items. |
| LLM-PROMPT-001 | Prompts must be explicitly versioned and version propagation must stay observable | LLM Runtime | Applicable | The agent still uses versioned prompts and the SQL tool changes prompt-facing behavior indirectly. |
| LLM-EXPOSE-001 | Operational exposure must flow through application modules | LLM Runtime | Applicable | The new capability should flow through an application module and tool definition, not directly from platform internals. |
| LLM-OBS-001 | LLM runtime monitoring must reuse the canonical observability runtime | LLM Runtime | Applicable | Query tool monitoring must reuse the current observability/event runtime. |

### Applicable Requirements

- **PRE-SCOPE-001 / PRE-SCOPE-003 / PRE-SCOPE-004:** One governed analytics tool is acceptable scaffold-stage work because it improves runtime extensibility without creating speculative product APIs.
- **PRE-SCOPE-002:** The sprint must avoid product-specific table design, broad CRM export semantics, and guessed business dashboards. It should use generic catalog and manifest language.
- **ARCH-CORE-001 / ARCH-LAYER-002 / ARCH-COMP-001:** The analytics query capability should live in its own module and depend on narrow ports rather than concrete DB or parser code.
- **ERR-CORE-001 / ERR-CODE-001 / ERR-TRANS-001 / ERR-REDACT-001:** Query validation, execution, and redaction failures must remain attributable, classified, and safe.
- **OBS-CORE-001 / OBS-CORR-001 / OBS-DIAG-001 / OBS-ALERT-001:** Query usage and failures must be visible through stable events, diagnostics, and correlation metadata.
- **TEST-SMOKE-001 / TEST-SMOKE-002 / TEST-FAIL-001:** The sprint changes a provider-backed runtime path and introduces new risky failure modes, so smoke and failure-path coverage are mandatory.
- **WF-SCOPE-001:** There is no justification for a workflow; the SQL capability is one explicit tool backed by a module-owned service.
- **LLM-TOOL-001 / LLM-LIFECYCLE-001 / LLM-RUN-001:** SQL remains an explicit tool with persisted tool-call lifecycle, approval, and inspectable results.

### Non-Applicable Requirements

- **ARCH-ENTRY-001 as a primary change driver:** The sprint does not add a new HTTP route; it reuses existing conversational/session entrypoints and tool execution.
- **WF-BOUNDARY-001 as an implementation driver:** No new workflow is expected, so this requirement matters mainly as a guardrail against accidental misuse.
- **LLM-IO-001:** The sprint does not introduce a new structured worker path; local validation still matters, but not through worker structured-output contracts.

### Ambiguous Or Conflicting Requirements

- **PRE-SCOPE-002 vs. semantic schema manifest depth:** The model needs enough semantic metadata to generate correct SQL, but too much domain modeling would drift into product design. The safe interpretation is to define a generic manifest format with relation/column semantics and sensitivity tags, while keeping the initial catalog intentionally small and clearly scaffold-grade.
- **LLM-LIFECYCLE-001 vs. current static approval model:** SQL risk is dynamic, but the current tool contract only supports static `requires_approval`. The safe interpretation for this sprint is to ship with a conservative static approval stance first, while designing the service and metadata so dynamic approval can be added cleanly later.

### Open Questions

- None remaining at reasoning completion.

## Feature Analysis

### Feature 1: Analytics Query Module And Schema-Agnostic Catalog

**Description:** Add a new bounded context that owns semantic catalog loading, query governance, execution orchestration, and result shaping for the SQL tool.

**Affected Areas**
- `backend/src/hello_sales_backend/modules/analytics_query/`
- `backend/src/hello_sales_backend/application/tools/`
- `backend/src/hello_sales_backend/platform/composition/`
- optional `backend/src/hello_sales_backend/platform/analytics_query/` only for neutral runtime-facing helpers if needed

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-CORE-001 | Explicit ownership of analytics-query behavior | new module boundary | File layout and import review |
| ARCH-LAYER-002 | Service depends on ports, not concrete parser/DB code | use-case/service constructors | Unit and integration tests |
| ARCH-COMP-001 | Module is wired through registrars | bootstrap/composition root | Integration coverage |
| PRE-SCOPE-003 | Prefer replaceable scaffolding over business assumptions | manifest/catalog/executor seams | Review of port boundaries |
| LLM-EXPOSE-001 | Capability exposed through app module | application tool calling module service | Tool and composition review |

**Current-System Analysis**
- Existing agent tools live in `application/tools/` and are intentionally small adapters over application services.
- The generic agent runtime in `platform/agents/runtime.py` already persists tool calls, approvals, results, and events. Sprint 5 should reuse that runtime rather than invent a second execution path.
- There is currently no analytics bounded context, no semantic catalog contract, and no redaction policy fit for SQL result sets.
- What must remain true is that `platform/` stays domain-neutral and the SQL capability’s governing policy does not leak into shared provider code.

**Options Considered**
- **Option A:** Put SQL validation and execution directly in a new application tool file.
- **Option B:** Add a dedicated `modules/analytics_query/` bounded context with ports for catalog, validator, executor, and redactor.
- **Option C:** Bury the capability in `platform/agents/` because it is “agent-only.”

**Chosen Approach**
- Adopt Option B. Create `modules/analytics_query/` as a bounded context with a narrow public service/facade, and keep the tool itself as a thin application-level adapter over that service.

**Decision Justification**
- Option B best satisfies the architecture contract because it gives the capability an explicit owner without overloading `platform/` or `application/tools/`.
- Option A would likely concentrate parser, execution, and redaction policy in the wrong layer and make later reuse harder.
- Option C would violate the platform neutrality requirement by embedding product-facing query policy inside runtime infrastructure.
- The module boundary also creates the right test seams for catalog, validator, executor, and redaction collaborators.

**Execution Notes**
- Define narrow ports such as `SchemaCatalogPort`, `QueryValidatorPort`, `AnalyticsQueryExecutorPort`, and `ResultRedactorPort`.
- Use a manifest format keyed by `catalog_id`, `catalog_version`, and `dialect` so the tool remains schema-agnostic.
- Use hand-authored YAML manifests for the initial catalog source.
- Keep the first catalog intentionally small, scaffold-grade, and backed by curated PostgreSQL views.

**Expected Evidence**
- **Tests:** unit tests for manifest normalization and service orchestration with fake ports; integration tests for module composition and one concrete catalog/executor path.
- **Runtime Evidence:** diagnostics and events expose catalog and dialect metadata where applicable.
- **Review Checks:** analytics-specific policy does not live in `platform/agents/`, `shared/`, or transport code.

---

### Feature 2: Governed SQL Tool Contract And Validation Pipeline

**Description:** Add one explicit agent tool, `query_analytics_data`, whose input accepts SQL and whose backend service validates it against a semantic catalog and policy before execution.

**Affected Areas**
- `backend/src/hello_sales_backend/application/tools/analytics_query.py`
- `backend/src/hello_sales_backend/application/agents/definitions/generic_agent/`
- `backend/src/hello_sales_backend/application/agents/definitions/observer_agent/`
- `backend/src/hello_sales_backend/platform/agents/tools.py`

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| LLM-TOOL-001 | Tool execution remains explicit and inspectable | one registered tool, persisted tool calls/results | Unit/integration/smoke evidence |
| LLM-LIFECYCLE-001 | Approval and rejection remain explicit | tool metadata and runtime pause state | Approval tests and review |
| ERR-CORE-001 | Unsafe SQL cannot fail silently | validator and policy failure paths | Failure-path tests |
| ERR-CODE-001 | Query policy failures need stable codes | validator and service error mapping | Unit tests and review |
| ERR-REDACT-001 | Result handling must redact safely | result shaping and returned payloads | Unit and integration tests |
| TEST-FAIL-001 | Negative paths must be tested | unsafe SQL / forbidden view / invalid AST / over-limit | Explicit negative tests |

**Current-System Analysis**
- `platform/agents/tools.py` already supports strict Pydantic input schemas and provider-facing tool definitions.
- The current runtime supports static `requires_approval` only.
- The existing redaction helper is general-purpose and key-name oriented; it is not sufficient for query result semantics.
- What must remain true is that the agent sees one explicit tool surface and the runtime continues to own lifecycle, approval, persistence, and replay semantics.

**Options Considered**
- **Option A:** Expose a raw `run_sql(sql: str)` tool against a read-only database role.
- **Option B:** Expose a governed `query_analytics_data` tool with strict input schema, semantic catalog checks, AST validation, execution limits, and redaction.
- **Option C:** Add several bespoke analytics tools instead of SQL.

**Chosen Approach**
- Adopt Option B. The agent gets one governed SQL tool with strict schema and service-backed validation/execution policy.

**Decision Justification**
- Option B preserves the power of SQL while preventing the tool surface from becoming arbitrary database access.
- Option A is operationally too risky and would violate the intent of the error, redaction, and pre-brief contracts.
- Option C would recreate the “too many tools” problem and still fail to cover ad hoc analytics well.
- The governance pipeline should be layered: manifest selection, AST validation, execution guardrails, redaction, truncation, and compact output shaping.

**Execution Notes**
- Tool input should include at least `catalog_id`, `sql`, `reason`, and optional `max_rows`.
- The validator must allow only one read-only statement (`SELECT` or `WITH ... SELECT`) and reject DDL/DML, transactions, temp tables, and access outside the approved catalog.
- Use `sqlglot` as the initial parser/AST library so the validator stays portable beyond a single dialect while still supporting strong policy checks now.
- Sprint 5 should ship with static approval enabled for this tool unless an uncontroversial dynamic approval seam can be added safely.

**Expected Evidence**
- **Tests:** unit coverage for validator rules, sensitivity/risk classification, and result shaping.
- **Runtime Evidence:** tool calls and results show catalog id, tool name, and approval state through current run/session inspection surfaces.
- **Review Checks:** the tool is one explicit capability and not a disguised raw database tunnel.

---

### Feature 3: Read-Only Execution, Redaction, And Result Shaping

**Description:** Execute validated SQL only against a curated read-only source, then redact, truncate, and shape results into a bounded agent-facing payload.

**Affected Areas**
- `modules/analytics_query/use_cases/`
- concrete executor adapter for the first dialect
- redaction and output-shaping components
- diagnostics/event emission around query metadata

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ERR-DATA-001 | Data-store failures remain loud and distinct | executor error mapping | Integration and failure-path tests |
| ERR-TRANS-001 | Cause and context survive translation | parser/executor/redactor errors | Error payload review |
| ERR-REDACT-001 | Redaction protects sensitive data without destroying diagnosis | result masking and error detail shaping | Unit tests |
| OBS-CORR-001 | Correlation survives execution boundary | query execution metadata and events | Observability tests/review |
| OBS-DIAG-001 | Operator-relevant state is inspectable | diagnostics/event payloads | Diagnostics coverage |
| TEST-INT-001 | Wiring and execution path need realistic coverage | concrete executor/cursor behavior | Integration tests |

**Current-System Analysis**
- The agent runtime already emits run/turn/tool-call events and persists tool state. Sprint 5 should enrich the tool result payload rather than add a parallel execution-log subsystem.
- SQL result sets create a different redaction problem from ordinary error details because sensitive meaning often lives in column semantics, not key names alone.
- The first implementation should not assume unrestricted row-level output is acceptable.

**Options Considered**
- **Option A:** Return raw rows as-is after SQL execution.
- **Option B:** Return redacted, truncated rows plus query metadata and a compact summary.
- **Option C:** Return only prose and hide structured query results.

**Chosen Approach**
- Adopt Option B. The tool returns a bounded structured result with metadata, redacted/truncated rows, and enough structure for the agent to reason over.

**Decision Justification**
- Option B best balances usefulness and governance.
- Option A is unsafe and would undermine the entire premise of a governed tool.
- Option C would hide inspectable result structure and make validation/review harder.
- The bounded result should expose query metadata such as `catalog_id`, `catalog_version`, `dialect`, `row_count`, `truncated`, `risk_flags`, and a query fingerprint.

**Execution Notes**
- Target PostgreSQL over curated analytics views for the first execution dialect and local development path.
- Use a separate read-only credential and curated analytics views only.
- Enforce statement timeout, max rows, and result truncation in the executor or service layer.
- Redaction should be semantics-aware through the manifest or redaction policy, not generic key-name heuristics.

**Expected Evidence**
- **Tests:** integration coverage for read-only execution, limits, and error translation; unit coverage for redaction behavior.
- **Runtime Evidence:** events and diagnostics show machine-usable query metadata and stable failure codes.
- **Review Checks:** result payloads are bounded and do not leak raw sensitive columns.

---

### Feature 4: Verification Strategy And Real-Provider Evidence

**Description:** Prove the governed SQL tool through deterministic tests and at least one real-provider smoke at the supported conversational boundary.

**Affected Areas**
- `backend/tests/unit/`
- `backend/tests/integration/`
- `backend/tests/smoke/`
- existing provider-backed smoke harness

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| TEST-SEAM-001 | Collaborators replaceable through public seams | fake catalog/validator/executor/redactor | Unit tests |
| TEST-INT-001 | Wiring and realistic boundaries covered | composition, persistence-adjacent execution, adapters | Integration tests |
| TEST-SMOKE-001 | Critical runtime path gets smoke coverage | agent SQL tool loop | Smoke tests |
| TEST-SMOKE-002 | Real-provider behavior proven at supported boundary | provider-backed generic agent smoke | Real-provider smoke or explicit deferral |
| TEST-DET-001 | Assertions stay durable | lifecycle/result-structure assertions | Test review |

**Current-System Analysis**
- The repo already has unit and integration coverage for the native tool-calling loop.
- The repo also now has a real-provider generic-agent baseline smoke harness.
- Sprint 5 should extend the existing smoke path rather than invent a second provider smoke entrypoint just for SQL.

**Options Considered**
- **Option A:** Rely on unit tests and fake-provider integration tests only.
- **Option B:** Add deterministic unit/integration coverage and extend the existing generic-agent smoke path to exercise the SQL tool.
- **Option C:** Add a separate ad hoc SQL smoke script outside the current smoke registry.

**Chosen Approach**
- Adopt Option B. Use deterministic local coverage plus centralized smoke coverage, including a real-provider generic-agent smoke scenario when environment support is present.

**Decision Justification**
- Option B aligns with the testing contract and current repo structure.
- Option A is not enough for a changed provider-backed conversational path.
- Option C would create a parallel smoke path with separate boot logic, which the process and testing contracts explicitly discourage.

**Execution Notes**
- Unit tests should focus on AST validation, policy, risk flags, and redaction.
- Integration tests should cover catalog loading, executor wiring, and failure translation.
- Smoke should prove the conversational runtime path rather than exact wording of the model response.

**Expected Evidence**
- **Tests:** unit, integration, negative, smoke, and real-provider smoke evidence recorded in the tracker.
- **Runtime Evidence:** smoke outputs confirm the SQL tool call/result path, not just text generation.
- **Review Checks:** the sprint records either the exact real-provider smoke run or a justified deferral.

## Deviations

| Requirement ID | Deviation | Reason | Risk | Disposition | Follow-up |
| --- | --- | --- | --- | --- | --- |
| LLM-LIFECYCLE-001 | Dynamic approval policy is deferred; the initial tool should use conservative static approval | Current runtime exposes static `requires_approval` and adding dynamic approval is a second-order runtime change | Aggregate queries may pause unnecessarily, which adds friction | Temporary | Design and implement dynamic approval metadata in the next sprint if operator feedback justifies it |
| PRE-SCOPE-002 | The first catalog will necessarily encode some relation and column semantics | The model needs semantic guidance to write correct SQL | The initial catalog could drift toward product-specific language if not kept intentionally narrow | Temporary | Keep the v1 catalog small, view-backed, and explicitly scaffold-grade; revisit once the product brief stabilizes |
| TEST-INT-001 / TEST-SMOKE-001 | Approval-path pytest teardown previously stalled after the session reached `completed` | `BackgroundTaskRunner.shutdown()` returned early when `_tasks` was empty and failed to await orphaned `_support_tasks` | Local verification could hang despite the runtime path succeeding | Resolved | Keep the runner fix in place and retain the approval-path integration and smoke checks in the normal pytest path |
| TEST-SMOKE-002 | A provider-backed analytics-query smoke was not completed in this workspace | The local environment did not produce review-grade evidence for the analytics-query provider path without the teardown issue | The SQL tool lacks one piece of desired environment-backed evidence | Temporary | Re-run the provider-backed generic-agent smoke for the analytics-query scenario after the teardown stall is fixed or in an environment closer to CI/runtime parity |

## Cross-Cutting Reasoning

### Major Decision Summary

- **One governed SQL tool rather than many bespoke tools:** chosen because it keeps the agent-facing surface small while still supporting search, filtering, grouping, and joins.
- **Agent tool, not worker:** chosen because the requirement is explicitly conversational tool use and the runtime already supports native tool calling with persisted lifecycle state.
- **Module-owned governance service:** chosen because catalog, AST validation, execution, and redaction policy are too substantial to live in a thin tool file or generic platform package.
- **Static approval first:** chosen because the runtime already supports it safely and dynamic approval is a distinct runtime enhancement.
- **Schema-agnostic semantic manifest:** chosen because raw DDL is not enough and hard-coding one schema would not survive future catalog or dialect changes.
- **`sqlglot` as the initial parser:** chosen because it provides real AST validation now without locking the validator to one long-term dialect implementation.
- **Hand-authored YAML as the initial catalog source:** chosen because it is the lowest-friction way to express semantic metadata, sensitivity tags, and allowed relations safely in Sprint 5.
- **PostgreSQL over curated views as the first dialect target:** chosen because it is the simplest local development and testing path while still proving the governed tool architecture.

### Trade-offs

- Shipping one tool keeps the public/runtime surface clean, but it pushes more responsibility into validation, governance, and result shaping.
- Using static approval in Sprint 5 is safer for first release, but less ergonomic for low-risk aggregate queries.
- A semantic manifest adds authoring overhead, but without it the model will generate SQL that is syntactically valid and semantically wrong.
- Restricting Sprint 5 to one dialect and one initial catalog limits breadth, but it is the right operational boundary for first release.
- Choosing `sqlglot` over a Postgres-only parser gives better extension headroom, but adds a more general dependency than a single-dialect implementation would require.
- Choosing YAML manifests over dbt-derived metadata keeps Sprint 5 simple and intentional, but creates a manual maintenance burden that may need replacement later.
- Choosing PostgreSQL over a warehouse adapter improves local iteration speed, but may leave some warehouse-specific policy or dialect issues for a later sprint.

### Assumptions

- The native tool-calling runtime currently on `main` remains the execution substrate for Sprint 5.
- A curated PostgreSQL read-only data source or view layer is available, or can be created, for the first catalog.
- The first SQL parser/executor choice can be made without forcing a long-term multi-dialect abstraction prematurely.
- The generic-agent smoke harness remains the canonical real-provider smoke path for conversational tool use.
- `sqlglot` is acceptable within the repo’s dependency posture for Sprint 5.

### Dependencies

- `ops/sprints/done/sprint-01-observability-foundation/`: provides the canonical event, metrics, tracing, and diagnostics seams Sprint 5 must reuse.
- `ops/sprints/done/sprint-02-worker-runtime-foundation/`: established the shared LLM substrate and earlier runtime boundary rules that Sprint 5 must respect.
- `ops/sprints/done/sprint-04-session-substrate-foundation/`: provides the session-first conversational API and attached execution surfaces through which the tool will be observed.
- Current native tool-calling runtime on `main`: Sprint 5 assumes the provider-native tool loop and tool lifecycle persistence are already in place.
- `sqlglot`: selected as the initial AST/parser dependency for SQL policy enforcement.
- Hand-authored YAML manifest files: selected as the initial semantic catalog source.
- PostgreSQL curated views: selected as the first execution target and local development path.

### Evidence Review Checklist

- Review can trace every major design decision back to explicit contract requirements.
- Review can verify that governance policy lives in a module-owned service rather than being smeared across tool, runtime, and provider layers.
- Review can verify that SQL validation, redaction, and execution failures use stable machine-usable codes.
- Review can verify that the tool remains one narrow capability and does not become arbitrary database access.
- Review can point to exact unit, integration, smoke, and real-provider smoke evidence or an explicit justified deferral.

## Phase Exit Criteria

- [x] Sprint scope is covered
- [x] Applicable requirements are mapped
- [x] Ambiguous and non-applicable requirements are recorded where relevant
- [x] Important decisions are explicitly justified
- [x] Non-trivial alternatives are discussed
- [x] Deviations, assumptions, risks, and unknowns are documented
- [x] Expected evidence is defined

## Documentation Updates

- `backend/docs/runtime-overview.md`: document the new analytics-query bounded context and its relationship to the conversational tool runtime.
- `backend/docs/agent-runtime.md`: document the governed SQL tool, approval stance, and result-shaping expectations.
- `backend/docs/testing-and-operations.md` or equivalent canonical testing/ops doc: record the SQL tool smoke path and any environment-gated real-provider evidence.
