# Frontend Architecture

## Purpose
This document explains the intended frontend architecture for HelloSales.

It complements:
- `ops/operational-contract/frontend.md`

## High-Level Shape

The frontend is organized into explicit ownership layers:

- `app/` for bootstrap, router, and global providers
- `pages/` for route-level assembly
- `features/` for bounded business capabilities
- `entities/` for reusable business-object representations
- `workflows/` for cross-feature journeys
- `shared/` for domain-neutral infrastructure and helpers
- `design-system/` for tokens, primitives, and reusable patterns
- `test/` for shared frontend test setup

## Intent

This structure exists to preserve:
- maintainability under growth
- migration flexibility from Vite to another host such as Next.js later
- strict ownership boundaries
- feature-local development
- a narrow, disciplined `shared/` layer

## Migration Readiness

The scaffold is intentionally migration-friendly:

- routing is isolated in `src/app/router/` and `src/pages/`
- environment access is isolated in `src/shared/config/`
- transport access is isolated in `src/shared/api/`
- most business code is plain React and TypeScript with no Vite-specific assumptions

If the brief later justifies Next.js, the host shell can change without rewriting the whole app.
