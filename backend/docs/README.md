# Backend Documentation

This is the canonical documentation set for the HelloSales backend codebase.

Use these docs to understand the implemented backend, its runtime boundaries, its public surfaces, and how to extend it safely.

Normative rules live outside the backend package under `ops/operational-contract/`.
These backend docs are implementation-oriented and describe the code as it exists today.

## Canonical Backend Docs

- **`runtime-overview.md`**
  High-level architecture, runtime model, and request / task / agent execution flow.

- **`codebase-map.md`**
  Package-by-package map of `src/hello_sales_backend/` and what each area owns.

- **`configuration-and-environment.md`**
  Runtime settings, provider configuration resolution, startup validation, and environment behavior.

- **`architecture-philosophy.md`**
  The codebase-level explanation of the architectural split, ownership model, and scaffold-stage philosophy.

- **`api-and-runtime-surfaces.md`**
  Public HTTP surfaces, operational surfaces, persistence/runtime seams, and key extension points.

- **`diagnostics-and-events.md`**
  Health, readiness, operational events, alerts, and diagnostics aggregation.

- **`agent-runtime.md`**
  Detailed explanation of the generic agent runtime, approvals, tools, lifecycle, and event model.

- **`errors-and-logging.md`**
  Codebase-level explanation of error philosophy, taxonomy usage, structured logging, and failure visibility.

- **`persistence-and-migrations.md`**
  Async SQLAlchemy runtime shape, stores, SQLite vs Postgres behavior, and migration workflow.

- **`testing-and-operations.md`**
  Tests, smoke harness, Postgres checks, and operational developer workflows.

## Relationship To Other Docs

- `backend/README.md` is the quick-start entrypoint for local development and common commands.
- `backend/docs/` is the canonical technical documentation set for the backend codebase.
- `ops/operational-contract/` contains normative contracts and review criteria.
