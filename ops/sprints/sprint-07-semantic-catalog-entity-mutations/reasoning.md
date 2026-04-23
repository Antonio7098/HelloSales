# Sprint Reasoning: Semantic Catalog And Entity Mutations

> Project: HelloSales
> Sprint ID: sprint-07-semantic-catalog-entity-mutations
> Output: `ops/sprints/sprint-07-semantic-catalog-entity-mutations/reasoning.md`

## Overview

**Sprint:** Semantic Catalog And Entity Mutations
**Purpose:** Promote the current analytics-only catalog into one canonical semantic data catalog, then use projected views of that catalog to keep the governed SQL tool working while introducing generic, schema-driven entity create/edit tools with undo mechanics.
**Tracker:** `ops/sprints/sprint-07-semantic-catalog-entity-mutations/tracker.md`
**Depends On:** `ops/sprints/sprint-04-session-substrate-foundation/tracker.md`, `ops/sprints/sprint-05-governed-sql-tool/tracker.md`, `ops/sprints/sprint-06-web-search-capabilities/tracker.md`

This sprint addresses a schema ownership problem created by Sprint 5 and exposed by the planned edit/create tools.
The current analytics catalog repeats field metadata that also appears in product-specific request models, SQLAlchemy records, and future entity mutation schemas.
Adding separate create/edit schemas or product-specific request/upsert models would duplicate the same facts again.
The semantic catalog must become the one source of truth for agent-visible reads, creates, and edits.

The correct direction is one canonical semantic catalog with multiple capability-specific projections:
- analytics query projection for approved read-only SQL relations and columns
- entity mutation projection for agent-visible create/edit tools
- context entity reference projection for session-scoped opaque entity ids
- future discovery/UI/API schema projection if needed, explicitly out of Sprint 7 scope

This sprint should not expose raw write SQL, should not add one tool per entity, should not add delete/archive, and should not add a `get_entity_schema`/discover tool.
The tool schemas remain generic, while the semantic catalog supplies the entity-specific shape and constraints already present in the agent context.
It should add a generic mutation substrate with strict generic tool schemas, server-side resolution, validation, permission policy, approval, undo records, audit, and inspectable lifecycle state.

## Requirement Map

### Contract Coverage Reviewed For This Sprint

| Contract File | Area | Applicability | Why It Matters |
| --- | --- | --- | --- |
| `ops/operational-contract/architecture.md` | Module ownership, dependency direction, composition | Applicable | The semantic catalog and mutation service need explicit ownership and must not leak DB/session concerns into tools or routes. |
| `ops/operational-contract/errors.md` | Structured failures, data failures, redaction | Applicable | Catalog drift, invalid manifests, invalid mutations, stale versions, permission failures, undo failures, and persistence failures must be explicit. |
| `ops/operational-contract/observability.md` | Correlation, diagnostics, alertable events | Applicable | Entity mutations are high-value operational events and need correlated audit/diagnostic signals. |
| `ops/operational-contract/testing.md` | Unit, integration, smoke, failure coverage | Applicable | This sprint changes schema interpretation, composition, agent tools, and persistence-backed mutations. |
| `ops/operational-contract/workflows.md` | Workflow eligibility | Applicable | Single entity create/edit operations are not workflows; multi-step transactional workflows remain future work. |
| `ops/operational-contract/llm.md` | Tool boundaries, approvals, structured IO, persisted lifecycle | Applicable | Entity mutations are LLM-backed write tools and must be explicit, validated, approved, and inspectable. |
| `ops/operational-contract/pre-brief-scope.md` | Foundation vs product-specific commitments | Applicable | The sprint must build generic schema/mutation substrate and avoid broad product-specific CRM semantics. |

### Requirement Index Used In This Sprint

| Requirement ID | Title | Area | Applicability | Why It Matters For This Sprint |
| --- | --- | --- | --- | --- |
| PRE-SCOPE-001 | Foundation work may proceed before the brief | Pre-Brief Scope | Applicable | A semantic catalog substrate and generic mutation tools are reusable foundation. |
| PRE-SCOPE-002 | Product-specific commitments must wait for the brief | Pre-Brief Scope | Applicable | The sprint must not invent customer/product lifecycle rules or preserve product-specific request/upsert models as authoritative schema. |
| PRE-SCOPE-003 | Operational scaffolding should be favored over product assumptions | Pre-Brief Scope | Applicable | Schema projection, validation, and audit seams are safer than product-specific workflows. |
| PRE-SCOPE-004 | Public APIs must remain intentionally narrow before the brief | Pre-Brief Scope | Applicable | Add narrow agent tools, not broad product APIs. |
| ARCH-CORE-001 | Module boundaries must remain explicit | Architecture | Applicable | `semantic_catalog` and `entity_operations` need clear bounded ownership. |
| ARCH-CORE-002 | Dependency direction must point inward | Architecture | Applicable | Tools should call module services; use cases should depend on ports; infra should implement persistence. |
| ARCH-LAYER-002 | Use cases depend on ports, not infra | Architecture | Applicable | Mutation orchestration must depend on resolver, schema catalog, policy, executor, and diagnostics ports. |
| ARCH-ENTRY-001 | Transport adapters must stay thin | Architecture | Mostly Non-Applicable | No new public HTTP routes are required, though existing company-profile routes must not be thickened. |
| ARCH-MODULE-001 | Module public APIs must stay small and stable | Architecture | Applicable | Catalog and mutation modules should expose stable services, commands, views, and bootstrap only. |
| ARCH-COMP-001 | Composition must happen through registrars | Architecture | Applicable | New modules and tools must be wired through bootstrap/composition. |
| ARCH-SHARED-001 | Shared and platform code must stay domain-neutral | Architecture | Applicable | Catalog mechanics may be generic, but entity-specific policy should not move into `shared/` or runtime substrate. |
| ERR-CORE-001 | No failure may disappear | Errors | Applicable | Failed mutations and failed undo attempts must produce visible terminal tool state and structured errors. |
| ERR-SHAPE-001 | Operational errors must preserve the canonical shape | Errors | Applicable | Invalid ref, stale version, denied field, bad schema, and persistence failure need canonical error payloads. |
| ERR-CODE-001 | Error codes must be stable and machine-usable | Errors | Applicable | Operators need distinct codes for schema, policy, concurrency, permission, validation, and data failures. |
| ERR-TRANS-001 | Error translation must preserve cause and context | Errors | Applicable | Repository and validation exceptions must preserve target entity/ref and cause. |
| ERR-HTTP-001 | Transport adapters must preserve the operational signal | Errors | Indirectly Applicable | Existing session APIs surface tool failures and must preserve structured error meaning. |
| ERR-DATA-001 | Persistence and data failures must be loud and distinct | Errors | Applicable | Writes, undo application, and catalog persistence failures must not be hidden behind success-shaped outputs. |
| ERR-REDACT-001 | Redaction must protect secrets without destroying diagnosis | Errors | Applicable | Mutation audit/tool results must avoid leaking restricted values while preserving changed field names and policy context. |
| OBS-CORE-001 | Failures must produce structured operational signals | Observability | Applicable | Mutation success/failure should emit structured events. |
| OBS-CORR-001 | Correlation identifiers must survive subsystem boundaries | Observability | Applicable | Request, trace, actor, run, turn, and tool ids must follow schema resolution and mutation execution. |
| OBS-DIAG-001 | Diagnostics surfaces must expose operator-relevant state | Observability | Applicable | Operators need inspectable catalog version and recent mutation/undo/audit state. |
| OBS-ALERT-001 | High-severity signals must be machine-usable for alerting | Observability | Applicable | Repeated denied/stale/failed mutations should be distinguishable by stable code. |
| TEST-SEAM-001 | Collaborators must be replaceable through public seams | Testing | Applicable | Schema catalog, ref resolver, policy evaluator, executor, audit, and diagnostics need fakes. |
| TEST-UNIT-001 | Business logic must have unit coverage | Testing | Applicable | Manifest validation, projections, mutation validation, undo planning, and risk policy are deterministic logic. |
| TEST-INT-001 | Wiring and persistence changes must have integration coverage | Testing | Applicable | Composition, existing analytics tool compatibility, and company-profile/product mutations need integration tests. |
| TEST-SMOKE-001 | Critical runtime paths must have smoke coverage | Testing | Applicable | Generic agent create/edit path should be exercised through centralized smoke or integration-level lifecycle coverage. |
| TEST-SMOKE-002 | Critical external provider paths must have real-provider smoke coverage | Testing | Applicable | Adding write-capable agent tools changes provider-backed tool behavior and needs real-provider smoke or explicit deferral. |
| TEST-FAIL-001 | Failure paths must be tested explicitly | Testing | Applicable | Unknown field, non-editable field, invalid ref, stale version, denied mutation, undo conflict, and persistence failure need negative tests. |
| TEST-DET-001 | Tests must remain deterministic and non-brittle | Testing | Applicable | Assertions should target schema/tool lifecycle/state, not model phrasing. |
| WF-SCOPE-001 | Workflows must be used only for real orchestration | Workflows | Applicable | One entity mutation is not a workflow. |
| WF-STATE-001 | Workflow outcomes must be explicit and inspectable | Workflows | Non-Applicable | No workflow is expected in this sprint. |
| WF-RETRY-001 | Retry and cancellation semantics must be explicit | Workflows | Non-Applicable | No long-running workflow retry/cancellation is expected. |
| LLM-BOUNDARY-001 | Shared substrate, runtime mechanics, and mode-specific policy must stay separated | LLM Runtime | Applicable | Mutation policy belongs in modules/application tools, not generic LLM/provider runtime. |
| LLM-TOOL-001 | Tool execution boundaries must stay explicit and mode-scoped | LLM Runtime | Applicable | Create/edit must be explicit conversational tools in allowed bundles. |
| LLM-IO-001 | Structured input and output boundaries must stay explicit when used | LLM Runtime | Applicable | Tool arguments and returned payloads need strict schemas and local validation. |
| LLM-LIFECYCLE-001 | Lifecycle controls must stay explicit and inspectable | LLM Runtime | Applicable | Approval, rejection, stale writes, and failures must remain visible. |
| LLM-RUN-001 | Runs and events must be durable or inspectable | LLM Runtime | Applicable | Mutation tool calls/results/failures should be persisted in run/session history. |
| LLM-PROMPT-001 | Prompts must be explicitly versioned and version propagation must stay observable | LLM Runtime | Applicable | Prompt policy changes for write tools require prompt version bump and runtime propagation. |
| LLM-EXPOSE-001 | Operational exposure must flow through application modules | LLM Runtime | Applicable | Tools should delegate to module services, not platform internals. |
| LLM-OBS-001 | LLM runtime monitoring must reuse canonical observability | LLM Runtime | Applicable | Tool monitoring should use existing run/tool/session/observability paths. |

### Applicable Requirements

- **PRE-SCOPE-001 / PRE-SCOPE-003 / PRE-SCOPE-004:** A unified semantic catalog and generic mutation substrate are valid foundation work if kept narrow and scaffold-grade.
- **PRE-SCOPE-002:** The sprint may migrate existing scaffold entities into the catalog, but the catalog must become authoritative and product-specific request/upsert models must not remain the agent-write contract.
- **ARCH-CORE-001 / ARCH-LAYER-002 / ARCH-COMP-001:** Catalog projection and mutation execution require bounded modules, ports, and composition wiring.
- **ERR-CORE-001 / ERR-SHAPE-001 / ERR-DATA-001 / ERR-REDACT-001:** Write tools must never hide failed writes or undo failures, and must not leak sensitive changed values in audit/tool results.
- **OBS-CORE-001 / OBS-CORR-001 / OBS-DIAG-001:** Mutations need structured correlated observability and diagnostics.
- **TEST-SEAM-001 / TEST-UNIT-001 / TEST-INT-001 / TEST-FAIL-001:** Schema projections and mutation policy are deterministic and must be fakeable and covered negatively.
- **LLM-TOOL-001 / LLM-IO-001 / LLM-LIFECYCLE-001 / LLM-RUN-001:** Entity create/edit tools must be explicit, strict, approved, undoable where possible, and persisted in the existing conversational lifecycle.

### Non-Applicable Requirements

- **ARCH-ENTRY-001 as a primary driver:** The sprint should not add new public HTTP routes unless absolutely necessary.
- **WF-STATE-001 / WF-RETRY-001:** Single create/edit actions are not workflows. Multi-step mutations with compensation are future work.
- **OBS-HEALTH-001:** The sprint does not materially change readiness except for catalog load failures, which should fail startup if required catalog files are invalid.

### Ambiguous Or Conflicting Requirements

- **One canonical catalog vs module ownership:** A central catalog risks becoming a god schema if it owns all business behavior. The safe split is shared semantic metadata in `semantic_catalog`, with analytics and mutation policy expressed as projections and owned by their capability modules.
- **Static approval vs dynamic risk:** Current tools support static `requires_approval`. Entity writes should ship with conservative static approval first; dynamic approval by field/entity sensitivity can follow once the runtime has a safe policy seam.
- **Removing product-specific request/upsert models:** The current code has product-specific Pydantic request models. Sprint 7 should not preserve these as authoritative agent-write schemas. If transport routes remain temporarily, they should validate against catalog-backed commands or be documented as compatibility wrappers, not sources of truth.
- **Context entity ids vs durable ids:** Opaque context refs should be session/run-scoped to prevent the agent from editing arbitrary ids. Durable database primary keys should remain server-side implementation details.
- **Undo semantics vs arbitrary side effects:** Undo is straightforward for create/edit against local persisted entities if before/after snapshots are captured. Undo is not a promise for future external side effects unless those adapters explicitly implement compensating actions.

### Open Questions

- Should dynamic approval policy be designed now as metadata only, even if enforcement remains static? The likely answer is yes: record policy metadata in the catalog, enforce static approval in the runtime.
- Should undo be exposed as an agent tool in Sprint 7 or implemented as an operator/internal service first? The safer Sprint 7 default is to implement undo records and service mechanics, then decide whether `undo_entity_mutation` is safe to expose after tests prove conflict handling.

## Feature Analysis

### Feature 1: Canonical Semantic Catalog Module

**Description:** Replace the analytics-only manifest with a canonical semantic catalog that can describe entities, fields, relationships, storage hints, sensitivity, and capability-specific projections.

**Affected Areas**
- `backend/src/hello_sales_backend/modules/semantic_catalog/`
- `backend/catalogs/semantic/scaffold_stage.yaml`
- `backend/src/hello_sales_backend/modules/analytics_query/`
- `backend/src/hello_sales_backend/platform/composition/`
- `backend/docs/`

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-CORE-001 | Catalog ownership is explicit | new `semantic_catalog` bounded context | File layout and exports |
| ARCH-LAYER-002 | Consumers depend on ports/projections | analytics and mutations consume catalog ports | Unit/integration tests |
| PRE-SCOPE-003 | Catalog remains scaffold-grade and reusable | generic entity/field metadata | Manifest review |
| ERR-CORE-001 | Invalid manifests fail loudly | loader validation and startup behavior | Negative tests |
| TEST-UNIT-001 | Projection logic is deterministic | manifest parser/projectors | Unit tests |

**Current-System Analysis**
- Sprint 5 created `backend/catalogs/analytics/scaffold_stage.yaml` with `relations` and `columns`.
- `modules/analytics_query/infra/catalogs.py` currently owns Pydantic manifest models and maps them directly to `AnalyticsCatalog`.
- Product-specific request/view models and SQLAlchemy records already define overlapping field names and types for `company_profiles` and `products`.
- Keeping product-specific request/upsert models or a second mutation schema as authoritative would create multiple sources of truth for the same fields.

**Options Considered**
- **Option A:** Keep analytics catalog as-is and create a separate entity mutation schema.
- **Option B:** Make the analytics catalog canonical and add write metadata directly to analytics relations.
- **Option C:** Introduce a canonical semantic catalog with separate projections for analytics and mutations.

**Chosen Approach**
- Adopt Option C. Create `modules/semantic_catalog` and migrate the YAML to a generalized catalog format.

**Decision Justification**
- Option C removes duplicated field metadata without forcing read analytics and write mutation policy into one flat model.
- Option A is the simplest short-term path but guarantees drift.
- Option B overloads analytics concepts such as `relations` and `columns` with write semantics such as `editable`, `required_on_create`, and optimistic concurrency.
- A canonical catalog plus projections keeps shared facts shared and capability policy separate.

**Execution Notes**
- Define semantic models such as `SemanticCatalog`, `SemanticEntity`, `SemanticField`, `SemanticRelationship`, `AnalyticsRelationProjection`, and `EntityMutationProjection`.
- Include shared metadata: `data_type`, `semantic_type`, `description`, `sensitivity`, identifier fields, display label, storage hints, and relationships.
- Include capability policy in scoped sections: `analytics` for SQL read projection and `mutations` for create/edit rules.
- Keep the initial catalog scaffold-grade and based only on existing persisted entity surfaces plus existing analytics aggregate relations.
- Treat product-specific request/upsert models as migration targets to remove or wrap, not as ongoing schema authorities.

**Expected Evidence**
- Unit tests load and validate the semantic manifest.
- Unit tests project the semantic catalog into the same effective analytics catalog used by the current SQL validator.
- Invalid manifests produce stable `semantic_catalog.*` error codes.

---

### Feature 2: Analytics Query Compatibility Projection

**Description:** Refactor the governed SQL tool to consume an analytics projection from the semantic catalog without changing the agent-facing `query_analytics_data` tool contract.

**Affected Areas**
- `modules/analytics_query/use_cases/ports.py`
- `modules/analytics_query/infra/catalogs.py`
- `modules/analytics_query/bootstrap.py`
- `application/agents/definitions/generic_agent/agent.py`
- tests and docs for analytics query

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| LLM-TOOL-001 | Existing SQL tool lifecycle stays explicit | no tool contract regression | Integration tests |
| ERR-TRANS-001 | Catalog projection failures preserve cause | projection loader errors | Negative tests |
| TEST-INT-001 | Wiring compatibility is proven | app factory/tool tests | Integration tests |
| PRE-SCOPE-004 | No new broad public surface | same SQL tool contract | Review |

**Current-System Analysis**
- The generic agent currently builds prompt schema text by reading the analytics query service catalog internals.
- The SQL validator depends on `AnalyticsCatalog`, `AnalyticsCatalogRelation`, and `AnalyticsCatalogColumn`.
- The tool contract already has stable arguments: `catalog_id`, `sql`, `reason`, and `max_rows`.

**Options Considered**
- **Option A:** Rewrite SQL validator to use semantic catalog objects directly.
- **Option B:** Keep validator unchanged and build `AnalyticsCatalog` from semantic catalog projection.
- **Option C:** Run both catalogs during a transition period.

**Chosen Approach**
- Adopt Option B. Preserve the existing analytics use-case models and have the loader/projector produce them from the canonical catalog.

**Decision Justification**
- Option B minimizes risk to the governed SQL tool and keeps Sprint 7 focused on unifying schema ownership.
- Option A may be cleaner later, but it expands the blast radius into SQL validation and redaction logic.
- Option C avoids immediate refactor but preserves duplicate truth and drift.

**Execution Notes**
- Replace or adapt `YamlAnalyticsCatalogStore` into an adapter backed by `SemanticCatalogService`.
- Keep `catalog_id=scaffold_stage` working.
- Preserve `catalog_version`, `dialect`, relation names, column sensitivity, risk flags, and result redaction behavior.

**Expected Evidence**
- Existing analytics unit and integration tests still pass after migration.
- A regression test verifies `company_profiles` and `products` analytics fields are projected from the canonical entity field metadata.

---

### Feature 3: Context Entity References

**Description:** Add session-scoped opaque entity references so the agent can edit “this record” or “the current entity” without seeing table names or primary-key write paths.

**Affected Areas**
- `platform/sessions/models.py`
- `platform/sessions/attachment.py`
- `modules/sessions/`
- `modules/entity_operations/`
- persistence/migration if durable context refs are needed

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| LLM-RUN-001 | Refs are inspectable with session/run context | session chronology/ref state | Integration tests |
| ERR-CORE-001 | Invalid/stale refs fail visibly | resolver errors | Negative tests |
| ERR-REDACT-001 | Refs hide raw persistence ids where needed | tool-visible payloads | Review/tests |
| OBS-CORR-001 | Refs preserve actor/session metadata | resolver context | Tests/events |

**Current-System Analysis**
- The session substrate records user, assistant, tool call, and tool result items.
- Tool results can already carry structured payloads into session chronology.
- There is no canonical place today for “entity mentioned in context” metadata.

**Options Considered**
- **Option A:** Let tools accept raw entity ids and entity types.
- **Option B:** Store opaque context refs in session/tool result payloads only.
- **Option C:** Add a context entity reference resolver with optional durable session-scoped ref storage.

**Chosen Approach**
- Adopt Option C if persistence is straightforward; otherwise ship an in-memory/session-payload resolver with explicit deferral for durable refs.

**Decision Justification**
- Option A exposes persistence details and allows the agent to guess write targets.
- Option B is simple but makes ref validation and versioning harder.
- Option C gives a real authority for resolving `entity_ref` to server-side entity identity, version, permissions, and display metadata.

**Execution Notes**
- Tool-visible refs should be opaque strings such as `ctx_entity_...`.
- Resolver records should include entity type, backing module, primary key or singleton marker, version, display label, session id, actor id, created/expiry time, and allowed operations.
- Initial refs can be emitted by company context reads and mutation tool results.

**Expected Evidence**
- Tests prove unknown refs, expired refs, wrong-session refs, and stale versions fail with stable validation/concurrency codes.
- Tool results show opaque refs and changed field names, not raw table names.

---

### Feature 4: Generic Entity Create/Edit Tools

**Description:** Add strict agent tools for `create_entity` and `edit_entity`, backed by a module-owned entity operation service and semantic catalog projections already supplied in context.

**Affected Areas**
- `backend/src/hello_sales_backend/modules/entity_operations/`
- `backend/src/hello_sales_backend/application/tools/entity_operations.py`
- `backend/src/hello_sales_backend/application/agents/definitions/generic_agent/`
- `backend/src/hello_sales_backend/platform/composition/`

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| LLM-TOOL-001 | Tools are explicit and allowed | generic-agent tool catalog | Tool registration tests |
| LLM-IO-001 | Tool schemas are strict and locally validated | generic Pydantic arg/result envelopes plus catalog validation | Unit tests |
| LLM-LIFECYCLE-001 | Writes require approval and inspectable state | `requires_approval=True`, persisted tool calls | Integration/smoke tests |
| ARCH-LAYER-002 | Mutation service depends on ports | resolver/policy/executor/diagnostics ports | Unit tests with fakes |
| ERR-DATA-001 | Persistence failures are loud | executor error mapping | Failure tests |

**Current-System Analysis**
- Application tools are thin adapters over module services.
- Agent tool definitions already support strict schemas and static approval.
- Existing product-specific create/update paths are temporary implementation details. Sprint 7 should move the write contract to catalog-backed generic commands and avoid preserving product-specific request/upsert models as the authoritative path.

**Options Considered**
- **Option A:** Add one `mutate_entity` tool with operation enum.
- **Option B:** Add separate `create_entity` and `edit_entity` tools, relying on semantic catalog context for schema.
- **Option C:** Add one tool per entity such as `edit_product` or another entity-specific edit tool.
- **Option D:** Add `get_entity_schema` as a discovery tool in the same sprint.

**Chosen Approach**
- Adopt Option B. Keep create and edit separate, and do not add schema discovery in Sprint 7.

**Decision Justification**
- Option B keeps the tool surface small while preserving clear semantics for validation, approval, idempotency, and model prompting.
- Option A is minimal but mixes create/edit semantics and increases ambiguous arguments.
- Option C does not scale and contradicts the minimum-tool philosophy established by the SQL tool.
- Option D may be useful later, but it is redundant in Sprint 7 because the semantic catalog is already the source of truth supplied to the agent context.

**Execution Notes**
- `create_entity({entity_type, values, reason})` validates against catalog create policy and delegates to an entity executor.
- `edit_entity({entity_ref, changes, expected_version, reason})` resolves the ref, validates editable fields, checks optimistic concurrency, delegates to executor, and returns updated ref/version/changed fields.
- Do not implement raw SQL updates. The executor should call module-owned services or repository ports.
- Register tools only on the generic agent unless another profile has explicit policy.
- Require approval for create/edit in Sprint 7.
- Do not add delete/archive in Sprint 7.
- Do not add `get_entity_schema` in Sprint 7. If later context windows require schema-on-demand, design a separate discovery tool then.
- Replace product-specific agent-write request/upsert models with catalog-backed generic command validation.

**Expected Evidence**
- Unit tests cover strict argument schemas, unknown fields, non-editable fields, missing required fields, stale versions, and sensitivity/risk classification.
- Integration tests exercise generic-agent tool lifecycle through approval into catalog-backed entity create/edit.
- Session chronology includes tool call, approval, and redacted result metadata.

---

### Feature 5: Undo, Audit, Observability, Prompt Policy, And Docs

**Description:** Make mutations undoable where possible, operationally visible, audit-friendly, and safe for the generic agent prompt policy.

**Affected Areas**
- `modules/entity_operations/infra/observability.py`
- `platform/observability/`
- `application/agents/definitions/generic_agent/prompts.py`
- `backend/docs/agent-runtime.md`
- `backend/docs/runtime-overview.md`
- `backend/docs/testing-and-operations.md`

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ERR-REDACT-001 | Audit protects sensitive values | redacted event/tool payloads | Unit/review |
| OBS-CORE-001 | Success/failure emits structured signals | mutation events | Integration tests |
| LLM-PROMPT-001 | Prompt behavior changes are versioned | generic prompt version bump | Prompt tests/docs |
| LLM-LIFECYCLE-001 | Undo lifecycle is explicit | undo records, conflict states, events | Unit/integration tests |
| TEST-SMOKE-001 | Runtime path is verified | centralized smoke or integration scenario | Smoke/integration evidence |

**Current-System Analysis**
- Analytics and web search already emit structured events and preserve tool lifecycle state.
- Generic-agent prompt policy distinguishes governed SQL and public web search.
- Write tools introduce a stronger safety requirement than read/query tools.
- Undo requires before/after snapshots and conflict detection, not just a prose audit note.

**Options Considered**
- **Option A:** Rely only on persisted tool call records for audit.
- **Option B:** Add module-level mutation audit/observability events in addition to tool-call records.
- **Option C:** Add a separate audit database table in Sprint 7.
- **Option D:** Add undo records with before/after snapshots and an internal undo service, but defer exposing undo as an agent tool until conflict handling is proven.

**Chosen Approach**
- Adopt Option D plus Option B. Add structured operational events, redacted tool results, and undo records sufficient to reverse create/edit where no conflicting later change has occurred.

**Decision Justification**
- Tool calls alone show invocation lifecycle but do not fully express entity mutation semantics.
- Undo cannot be reconstructed reliably from logs alone; the mutation layer must capture before/after state, catalog version, entity version, and inverse operation metadata.
- A durable mutation/undo record is justified because create/edit are write operations and the user explicitly requires undo mechanics.
- Exposing undo to the agent can be deferred until internal mechanics and conflict states are verified.

**Execution Notes**
- Create a mutation record for every successful create/edit with operation id, entity type, entity ref, catalog id/version, actor/request/trace ids, tool call id, before snapshot, after snapshot, changed fields, version before/after, and undo status.
- For create undo, plan the inverse as a catalog-declared compensation only if the entity supports safe reversal and no later dependent/conflicting change exists. Do not expose delete/archive as a general tool.
- For edit undo, plan the inverse as restoring prior field values only if the current entity version still matches the mutation's after version.
- Represent undo outcomes explicitly: `available`, `applied`, `conflicted`, `unavailable`, `failed`.
- Emit `entity_operations.mutation.created`, `entity_operations.mutation.updated`, `entity_operations.undo.applied`, `entity_operations.undo.conflicted`, and `entity_operations.mutation.failed` events with entity type, opaque ref, changed field names, version before/after, actor/request/trace ids, and redacted error detail.
- Update prompt policy to instruct the agent to use context refs, ask clarifying questions when target/entity is ambiguous, avoid inventing values, and expect approval for writes.
- Bump generic prompt version.

**Expected Evidence**
- Docs explain one semantic catalog, analytics projection, entity mutation projection, context refs, approval stance, undo mechanics, and safety guarantees.
- Tests verify sensitive values are not emitted in tool results/events.
- Tests verify edit undo restores previous values when no conflict exists and rejects/conflicts when the entity version has moved.

## Deviations, Risks, Assumptions, And Unknowns

### Planned Deferrals

- **Dynamic approval policy:** Catalog may include policy metadata, but runtime enforcement remains static approval for write tools in Sprint 7.
- **Discovery tool:** Defer `get_entity_schema` or broader discovery until schema-on-demand is needed; Sprint 7 supplies schema through the canonical catalog/context.
- **Delete/archive tool:** Explicitly out of scope.
- **Agent-facing undo tool:** Defer unless implementation proves conflict handling and approval semantics are safe enough to expose; internal undo records/mechanics are in scope.

### Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Semantic catalog becomes a god schema | High | Keep it to metadata, validation, and projections; keep execution side effects in capability modules. |
| Analytics regression from catalog migration | High | Preserve `AnalyticsCatalog` use-case model and add compatibility tests before changing validator behavior. |
| Agent edits wrong record | High | Use opaque session-scoped refs, expected version, approval, and strict resolver checks. |
| Sensitive mutation values leak into events/tool results | High | Return changed field names and redacted summaries, not raw restricted values. |
| Undo applies over conflicting later changes | High | Require version checks and explicit `conflicted` status before applying inverse changes. |
| Product-specific request/upsert models remain authoritative | High | Move create/edit validation to catalog-backed generic commands and treat legacy transport models as compatibility wrappers or remove them. |

### Assumptions

- Static approval is acceptable for all create/edit tools in Sprint 7.
- The SQL tool contract should not change externally.
- The generic agent remains the only profile receiving analytics and entity mutation tools unless explicitly revised.
- Schema content will be supplied to the agent context; schema discovery tooling is out of scope.

## Execution Updates

### Implemented Outcome

- The canonical semantic manifest now lives at `backend/catalogs/semantic/scaffold_stage.yaml`, and the legacy analytics-only manifest has been removed from the authoritative runtime path.
- `modules/semantic_catalog/` now owns manifest loading, duplicate/projection validation, and stable `semantic_catalog.*` config errors.
- `modules/analytics_query/` now consumes a projection adapter built from the semantic catalog instead of loading analytics YAML directly.
- `modules/entity_operations/` now owns generic create/edit validation, signed context refs, approval-facing tool execution, undo record capture, undo conflict checks, and correlated observability.
- The generic agent prompt and tool bundle now include `create_entity` and `edit_entity`, with static approval required for both tools.
- Session context replay now includes prior tool-result payloads so previously issued entity refs and versions can flow into later turns without exposing raw storage ids.

### Recorded Deferrals

- Durable context-ref persistence remains deferred. Sprint 7 ships signed session-scoped refs derived from session/tool context rather than a dedicated persistence table.
- `undo_entity_mutation` remains an internal/service capability only. The sprint records undo metadata and conflict handling, but does not expose an agent-facing undo tool.
- Centralized generic-agent smoke coverage for the entity edit path was deferred in favor of deterministic integration coverage because the existing smoke harness already has approval complexity and no stable multi-approval write scenario baseline.
- Real-provider write smoke remains deferred because Sprint 7 did not introduce a safe provider-backed mutation fixture with approval automation.

### Verification Evidence

- `pytest backend/tests/unit backend/tests/integration -q`
- `pytest backend/tests/smoke -q`
- Result: `96` unit/integration tests passed; `10` smoke tests passed and `3` smoke tests were skipped for existing provider-environment reasons.

## Exit Criteria

- One canonical semantic catalog exists and replaces the standalone analytics catalog as source of field metadata.
- The governed SQL tool still works through an analytics projection with no agent-facing contract change.
- Generic create/edit tools exist with strict generic schemas, catalog-backed validation, and conservative approval.
- Product-specific request/upsert models are removed from the authoritative write path or converted into compatibility wrappers over catalog-backed commands.
- Entity refs are opaque and server-resolved rather than raw table/id write paths.
- Undo records/mechanics exist for create/edit, with explicit available/applied/conflicted/unavailable/failed states.
- Mutation validation, undo behavior, failures, approval lifecycle, observability, and redaction are covered by tests.
- Canonical docs describe the unified catalog and mutation safety model.
