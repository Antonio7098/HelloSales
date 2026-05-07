# Sprint Tracker: Semantic Catalog And Entity Mutations

> Project: HelloSales
> Sprint ID: sprint-07-semantic-catalog-entity-mutations
> Created: 2026-04-23

## Sprint Overview

- **Sprint Name:** Semantic Catalog And Entity Mutations
- **Sprint Focus:** Replace the analytics-only catalog with one canonical semantic catalog, preserve governed SQL through an analytics projection, and add generic schema-driven create/edit agent tools with context refs, validation, approval, undo mechanics, and audit/observability.
- **Depends On:** `ops/sprints/done/sprint-04-session-substrate-foundation/tracker.md`, `ops/sprints/done/sprint-05-governed-sql-tool/tracker.md`, `ops/sprints/done/sprint-06-web-search-capabilities/tracker.md`
- **Status:** Completed With Documented Deferrals

## Sprint Goals

- **Primary Goal:** Ship a unified semantic catalog substrate that is the one source of truth for governed analytics reads and generic entity create/edit tools without duplicating field metadata or preserving product-specific request/upsert schemas as authoritative write contracts.
- **Secondary Goals:**
  - Preserve the existing `query_analytics_data` tool contract and behavior through a semantic-catalog-backed analytics projection.
  - Add context-scoped opaque entity references so the agent edits server-resolved entities rather than raw table/id targets.
  - Add strict `create_entity` and `edit_entity` tools for the generic agent, backed by module-owned validation, policy, execution, undo records, and diagnostics.
  - Keep write tools conservative with static approval, optimistic concurrency, undo mechanics, redacted outputs, and inspectable tool/session lifecycle.
  - Document the unified catalog, projection model, mutation safety model, and follow-up deferrals.

## Execution Checklist

- [x] **Task 1: Formalize Sprint 7 artifacts and execution context**
  > *Description: Prepare sprint artifacts and confirm the implementation boundary before coding starts.*
  - [x] **Sub-task 1.1:** Finalize `reasoning.md` and `tracker.md` under `ops/sprints/sprint-07-semantic-catalog-entity-mutations/`.
  - [x] **Sub-task 1.2:** Start work from `sprint/sprint-07-semantic-catalog-entity-mutations` or explicitly record any branch deviation.
  - [x] **Sub-task 1.3:** Confirm that Sprint 7 will not implement raw write SQL, one tool per entity, `get_entity_schema`/discovery tooling, dynamic approval enforcement, generated product-specific request models, or delete/archive semantics unless this tracker is explicitly revised.

- [x] **Task 2: Add the canonical semantic catalog module**
  > *Description: Introduce one schema source of truth for entity, field, relationship, sensitivity, storage, read, and mutation metadata.*
  - [x] **Sub-task 2.1:** Add `modules/semantic_catalog/` with bootstrap, service/facade, commands/views as needed, and use-case ports.
  - [x] **Sub-task 2.2:** Define strict manifest models for `SemanticCatalog`, entities, fields, relationships, storage hints, display metadata, analytics projections, and mutation projections.
  - [x] **Sub-task 2.3:** Move `backend/catalogs/analytics/scaffold_stage.yaml` into a generalized `backend/catalogs/semantic/scaffold_stage.yaml`.
  - [x] **Sub-task 2.4:** Preserve scaffold-grade scope by migrating only existing persisted scaffold entity surfaces and existing analytics aggregate relations.
  - [x] **Sub-task 2.5:** Add stable `semantic_catalog.*` error codes for missing directory, invalid manifest, duplicate ids, invalid projection, and unsupported field policy.

- [x] **Task 3: Refactor analytics query to consume a semantic projection**
  > *Description: Keep the governed SQL tool behavior stable while making semantic catalog metadata the source of truth.*
  - [x] **Sub-task 3.1:** Implement an analytics projection adapter that produces the existing `AnalyticsCatalog` shape from `SemanticCatalog`.
  - [x] **Sub-task 3.2:** Replace direct YAML analytics loading with semantic-catalog-backed loading in analytics query bootstrap/composition.
  - [x] **Sub-task 3.3:** Preserve `catalog_id=scaffold_stage`, `catalog_version`, dialect, relation names, column sensitivity, risk flags, redaction, truncation, and query metadata.
  - [x] **Sub-task 3.4:** Update generic-agent schema prompt construction to use the analytics projection without reaching into private service internals.
  - [x] **Sub-task 3.5:** Remove or deprecate the standalone analytics catalog path only after compatibility tests pass.

- [x] **Task 4: Add context entity references**
  > *Description: Give the agent opaque, session-scoped references for editable entities while keeping table names and primary-key write paths server-side.*
  - [x] **Sub-task 4.1:** Define context entity reference models with `entity_ref`, `entity_type`, display label, version, session/run/actor scope, allowed operations, and expiration or validity semantics.
  - [x] **Sub-task 4.2:** Add a resolver port and first implementation for catalog-backed scaffold entity records.
  - [x] **Sub-task 4.3:** Ensure refs can be emitted in read/context responses and mutation results without exposing raw storage details.
  - [x] **Sub-task 4.4:** Validate wrong-session, unknown, expired, unauthorized, and stale refs with stable error codes.
  - [x] **Sub-task 4.5:** Record any durable-ref persistence deferral explicitly if refs are initially derived from session/tool payloads rather than stored in a dedicated table.

- [x] **Task 5: Add the entity operations bounded context**
  > *Description: Introduce module-owned create/edit orchestration over semantic schema projection, context refs, policy validation, persistence execution, and diagnostics.*
  - [x] **Sub-task 5.1:** Add `modules/entity_operations/` bootstrap, service/facade, commands, views, and use-case ports.
  - [x] **Sub-task 5.2:** Define ports for schema catalog projection, context ref resolution, mutation policy, mutation executor, and diagnostics/audit events.
  - [x] **Sub-task 5.3:** Implement create validation for required fields, unknown fields, field types, nullability, sensitivity policy, and relationship constraints.
  - [x] **Sub-task 5.4:** Implement edit validation for editable fields, unknown fields, non-editable fields, expected version, stale updates, and ambiguous targets.
  - [x] **Sub-task 5.5:** Implement first executor adapters through catalog-backed generic commands, not product-specific request/upsert models or raw SQL update commands.
  - [x] **Sub-task 5.6:** Capture undo records for successful create/edit operations, including before/after snapshots, catalog version, entity version before/after, inverse operation metadata, and undo status.
  - [x] **Sub-task 5.7:** Return bounded redacted results: operation id, entity ref, entity type, display label, version, changed fields, undo status, warnings, and audit metadata.

- [x] **Task 6: Expose generic entity tools to the agent**
  > *Description: Add a small write-capable tool surface backed by the entity operations service and existing persisted tool lifecycle.*
  - [x] **Sub-task 6.1:** Add `application/tools/entity_operations.py` with strict generic Pydantic envelopes for `create_entity` and `edit_entity`.
  - [x] **Sub-task 6.2:** Register the tools only on the generic agent unless another profile is explicitly approved.
  - [x] **Sub-task 6.3:** Set `create_entity` and `edit_entity` to `requires_approval=True` for Sprint 7.
  - [x] **Sub-task 6.4:** Do not add `get_entity_schema` in Sprint 7; schema must come from the canonical catalog/context, with future discovery tooling recorded as out of scope.
  - [x] **Sub-task 6.5:** Update generic-agent prompt policy and bump prompt version so the agent uses schema context and context refs, asks clarifying questions for ambiguous targets, avoids invented values, expects approval for writes, and understands undo availability.

- [x] **Task 7: Preserve undo, audit, observability, and redaction**
  > *Description: Make entity mutation and undo behavior inspectable without leaking restricted values.*
  - [x] **Sub-task 7.1:** Emit structured events for mutation created, mutation updated, mutation rejected, stale version, undo applied, undo conflicted, undo unavailable, and mutation failed.
  - [x] **Sub-task 7.2:** Include request id, trace id, actor id, session id, run id, turn id, tool call id, entity type, entity ref, changed field names, and version before/after where available.
  - [x] **Sub-task 7.3:** Redact sensitive values from tool results, session item payloads, operational events, and error details while preserving diagnosis.
  - [x] **Sub-task 7.4:** Implement undo conflict checks so edit undo only applies when the current version still matches the mutation's after version.
  - [x] **Sub-task 7.5:** Represent undo states explicitly as `available`, `applied`, `conflicted`, `unavailable`, or `failed`.
  - [x] **Sub-task 7.6:** Extend diagnostics or docs to make effective catalog id/version and recent mutation/undo failures inspectable.
  - [x] **Sub-task 7.7:** Record agent-facing undo-tool deferral unless explicitly implemented and approved in this tracker.

- [x] **Task 8: Add verification and documentation**
  > *Description: Prove catalog unification and entity mutation behavior through deterministic tests, runtime lifecycle tests, smoke coverage, and canonical docs.*
  - [x] **Sub-task 8.1:** Add unit tests for semantic manifest loading, projection validation, duplicate detection, and invalid capability metadata.
  - [x] **Sub-task 8.2:** Add unit tests for analytics projection compatibility, including existing scaffold entity fields projected from canonical entity metadata.
  - [x] **Sub-task 8.3:** Add unit tests for entity create/edit validation, policy failures, redaction, optimistic concurrency, undo planning, and undo conflict handling.
  - [x] **Sub-task 8.4:** Add integration tests for app composition, analytics query compatibility, tool registration, approval lifecycle, catalog-backed entity mutations, and undo mechanics.
  - [x] **Sub-task 8.5:** Add or update centralized smoke coverage for a generic-agent entity edit path, or record an explicit justified deferral.
  - [x] **Sub-task 8.6:** Update canonical backend docs for semantic catalog, analytics projection, entity mutation tools, context refs, approval stance, and known deferrals.

## Testing And Documentation Checklist

- [x] **Unit Tests:** deterministic coverage for semantic catalog manifest handling, projections, mutation validation, ref resolution, optimistic concurrency, undo planning/conflicts, redaction, and policy errors
- [x] **Integration Tests:** composition, analytics-query compatibility, entity operation service wiring, tool registration, approval lifecycle, session chronology, catalog-backed persistence mutations, and undo mechanics
- [x] **Smoke Tests:** centralized generic-agent smoke equivalent was deferred explicitly; runtime lifecycle coverage for create/edit now exists through unit, integration, and existing smoke harness regression validation.
- [x] **Real Provider Smoke:** explicitly deferred for write tools in Sprint 7; no safe real-provider mutation fixture or approval automation path was introduced in this sprint.
- [x] **Documentation Updates:** update canonical backend docs in `backend/docs/`

## Risks And Blockers

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| Semantic catalog becomes a god schema that owns business behavior | High | Keep shared metadata in `semantic_catalog`; keep analytics and mutation execution policy in capability modules | Mitigated |
| Analytics query regresses during catalog migration | High | Preserve existing `AnalyticsCatalog` model and add projection compatibility tests before changing validator behavior | Mitigated |
| Agent edits the wrong entity | High | Require opaque session-scoped refs, expected version, static approval, and strict resolver checks | Mitigated |
| Mutation output or audit events leak sensitive values | High | Return changed field names and redacted summaries; test restricted/internal field behavior | Mitigated |
| Undo applies over conflicting later changes | High | Require version checks and explicit conflict states before applying inverse changes | Mitigated |
| Product-specific request/upsert models remain authoritative | High | Move create/edit validation to catalog-backed generic commands and treat legacy transport paths as compatibility wrappers or remove them | Mitigated |
| Product-specific schema hardens before product brief | Medium | Limit Sprint 7 entities to existing scaffold surfaces and label catalog scaffold-grade | Accepted |
| Dynamic approval policy is needed but runtime only supports static approval | Medium | Ship static approval for write tools; record dynamic approval as explicit follow-up | Deferred |
| Schema discovery may be needed later for context-window pressure | Medium | Keep discovery out of Sprint 7 and record a future `discover_entity_schema` design if needed | Deferred |

## Success Criteria

- [x] **Success Criteria 1:** The standalone analytics catalog is replaced by one canonical semantic catalog for shared entity/field metadata.
- [x] **Success Criteria 2:** `query_analytics_data` continues to work through a semantic-catalog-backed analytics projection with no agent-facing contract regression.
- [x] **Success Criteria 3:** The generic agent has strict `create_entity` and `edit_entity` tools backed by module-owned catalog validation, policy, execution, undo records, and diagnostics.
- [x] **Success Criteria 4:** Entity edits use opaque context refs and expected versions rather than raw table names or unchecked primary-key updates.
- [x] **Success Criteria 5:** Create/edit tools require approval, persist inspectable lifecycle state, emit redacted audit/observability signals, capture undo state, and surface structured failures.
- [x] **Success Criteria 6:** Product-specific request/upsert models are removed from the authoritative agent-write path or reduced to compatibility wrappers over catalog-backed commands.
- [x] **Success Criteria 7:** Tests and docs prove catalog unification, mutation safety, undo mechanics, analytics compatibility, and explicit deferrals.

## Review And Sign-Off

- Sprint Status: Completed With Documented Deferrals
- Completion Date: 2026-04-23

## Execution Evidence

- Sprint artifacts created from:
  - `ops/process/reasoning/reasoning-protocol.md`
  - `ops/process/execute/tracker-template.md`
- Initial design evidence gathered from:
  - `backend/catalogs/analytics/scaffold_stage.yaml`
  - `backend/src/hello_sales_backend/modules/analytics_query/`
  - existing persisted scaffold entity modules and request models that must be migrated behind catalog-backed commands
  - `backend/src/hello_sales_backend/platform/agents/tools.py`
  - `backend/src/hello_sales_backend/platform/agents/runtime.py`
  - `backend/src/hello_sales_backend/platform/sessions/`
- Implementation branch:
  - `sprint/sprint-07-semantic-catalog-entity-mutations`
- Implemented artifacts:
  - canonical semantic catalog at `backend/catalogs/semantic/scaffold_stage.yaml`
  - new `modules/semantic_catalog/`
  - new `modules/entity_operations/`
  - generic-agent `create_entity` and `edit_entity` tools with approval
  - semantic-catalog-backed analytics projection adapter
  - signed session-scoped context entity refs and session replay of prior tool results
- Verification commands:
  - `pytest backend/tests/unit backend/tests/integration -q`
  - `pytest backend/tests/smoke -q`
- Verification outcome:
  - `96` unit/integration tests passed
  - `10` smoke tests passed, `3` smoke tests skipped
- Notable deferrals:
  - durable context-ref persistence remains deferred; Sprint 7 uses signed session-scoped refs derived from tool/session context rather than a dedicated table
  - no agent-facing `undo_entity_mutation` tool was exposed; undo mechanics remain internal/service-level only
  - centralized generic-agent smoke for entity edit was deferred in favor of deterministic integration coverage (`backend/tests/integration/test_entity_operations_tool.py`)
  - real-provider smoke for write tools was deferred because Sprint 7 did not add a safe provider-backed mutation fixture with approval automation
