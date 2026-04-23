# Semantic Catalog And Entity Mutations

## Purpose
This document explains the backend's canonical semantic catalog and the generic entity mutation path introduced in Sprint 7.

It focuses on:
- the single source of truth for shared entity and analytics metadata
- how governed analytics still works through a projection
- how generic `create_entity` and `edit_entity` operate
- how opaque context refs, approvals, redaction, and undo behave
- what was intentionally deferred

## Canonical Catalog

The authoritative scaffold-stage manifest now lives at:
- `backend/catalogs/semantic/scaffold_stage.yaml`

The semantic catalog owns:
- entity ids and descriptions
- field names, types, nullability, semantic type, and sensitivity
- display metadata such as label fields
- storage hints such as relation name and primary key field
- analytics projection metadata
- mutation projection metadata
- relationship metadata

The semantic catalog does not own:
- raw SQL execution
- product-specific business workflows
- transport-specific request models
- dynamic approval enforcement

## Runtime Ownership

### `modules/semantic_catalog/`
Owns:
- semantic manifest loading
- duplicate and projection validation
- stable `semantic_catalog.*` config failures
- the small service/facade used by other modules

### `modules/analytics_query/`
Owns:
- governed SQL validation and execution
- redaction of SQL results
- analytics-specific observability

It now receives an `AnalyticsCatalog` projection from the semantic catalog rather than loading an analytics-only YAML directly.

### `modules/entity_operations/`
Owns:
- generic create/edit orchestration
- catalog-backed field validation
- signed context entity refs
- optimistic concurrency checks via `expected_version`
- bounded mutation results
- undo record capture and undo conflict logic
- mutation observability events

## Analytics Projection

The SQL tool contract did not change.

`query_analytics_data` still accepts:
- `catalog_id`
- `sql`
- `reason`
- `max_rows`

Internally, the analytics module now projects the semantic catalog into the existing `AnalyticsCatalog` shape.
This preserves:
- `catalog_id=scaffold_stage`
- catalog version and dialect
- approved relation and column names
- sensitivity-driven risk flags
- existing validator and redaction behavior

## Generic Entity Tools

The generic agent now exposes:
- `create_entity`
- `edit_entity`

These tools are generic on purpose.
Schema specifics come from the semantic catalog already included in agent context, not from a one-tool-per-entity surface and not from a `get_entity_schema` discovery tool.

### `create_entity`
Shape:
- `entity_type`
- `values`
- `reason`

Behavior:
- validates unknown fields, required fields, nullability, field types, and writable policy
- rejects restricted-field writes
- routes persistence through module-owned adapters instead of raw SQL
- returns a bounded redacted result with the new `entity_ref`, version, changed fields, warnings, and audit metadata

### `edit_entity`
Shape:
- `entity_ref`
- `changes`
- `expected_version`
- `reason`

Behavior:
- resolves the opaque ref server-side
- validates session/actor scope, expiry, allowed operations, and stale refs
- validates field mutability and payload types
- enforces optimistic concurrency with `expected_version`
- returns a refreshed opaque ref and updated version

## Context Entity Refs

Tool-visible entity ids are now opaque refs that begin with `ctx_entity_`.

Current ref behavior:
- signed with a backend-owned secret
- scoped to the originating session and actor when present
- carries allowed operations
- carries the entity version used when the ref was issued
- expires after the TTL declared by the semantic mutation projection

Current ref validation covers:
- unknown or malformed refs
- wrong-session refs
- unauthorized actor access
- expired refs
- stale refs whose version no longer matches persisted state

Current deferral:
- refs are not yet stored in a dedicated table; they are derived from signed session/tool context

## Approval, Redaction, And Undo

### Approval
`create_entity` and `edit_entity` both require static approval in Sprint 7.
Dynamic approval remains deferred.

### Redaction
Mutation tool results and emitted operational events intentionally avoid raw sensitive values.
They return:
- operation id
- entity ref
- entity type
- display label
- version
- changed field names
- undo status
- warnings
- audit correlation metadata

### Undo
Undo mechanics exist at the service layer.

Current behavior:
- successful edits record before/after snapshots, catalog version, and version before/after
- edit undo is only valid when the current entity version still matches the mutation's `version_after`
- create undo is marked unavailable because delete/archive semantics remain out of scope
- undo states are explicit: `available`, `applied`, `conflicted`, `unavailable`, `failed`

Current deferral:
- there is no agent-facing `undo_entity_mutation` tool yet

## Observability

Entity operations emit structured operational events for:
- `entity_operations.mutation.created`
- `entity_operations.mutation.updated`
- `entity_operations.mutation.rejected`
- `entity_operations.mutation.stale_version`
- `entity_operations.mutation.failed`
- `entity_operations.undo.applied`
- `entity_operations.undo.conflicted`
- `entity_operations.undo.unavailable`

These events carry correlated request / trace / actor / session / run / turn / tool-call metadata when available.

## Known Deferrals

- Dynamic approval enforcement by entity or field sensitivity
- Durable ref persistence
- Schema discovery tooling such as `get_entity_schema`
- Delete/archive semantics
- Agent-facing undo tool
- Real-provider smoke for write tools
