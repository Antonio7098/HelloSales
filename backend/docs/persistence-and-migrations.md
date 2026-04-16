# Persistence And Migrations

## Purpose
This document explains the backend's current persistence model and migration workflow.

It covers:
- async SQLAlchemy runtime assembly
- stores and persistence responsibilities
- SQLite vs Postgres behavior
- unit-of-work support
- migration workflow

## Persistence Runtime Shape

The database runtime is assembled in:
- `src/hello_sales_backend/platform/composition/app_container.py`

The container builds:
- SQLAlchemy async engine
- async session factory
- unit-of-work factory
- task run store
- agent store

This bundle is exposed as `DatabaseRuntime`.

## Async SQLAlchemy Standard

The backend uses async SQLAlchemy from the start.

Important runtime pieces include:
- `AsyncEngine`
- `async_sessionmaker`
- explicit session factory wiring
- async unit-of-work support

The goal is to keep async behavior explicit and avoid hidden sync/async mixing in the runtime layer.

## Unit Of Work

Unit-of-work primitives live in:
- `platform/db/uow.py`

Current pieces:
- `UnitOfWork` protocol
- `AsyncSqlAlchemyUnitOfWork`
- `build_uow_factory()`

The current unit of work is intentionally minimal.
It owns:
- one async SQLAlchemy session
- commit
- rollback
- session cleanup on exit

This is useful when future modules need explicit transaction boundaries beyond simple repository/store methods.

## Current Stores

The main persistence adapters live in:
- `platform/db/repositories.py`

### `SqlAlchemyTaskRunStore`
Owns:
- persisting background task snapshots
- updating structured error summary fields
- listing recent task runs

### `SqlAlchemyAgentStore`
Owns:
- run persistence
- turn persistence
- tool-call persistence
- artifact persistence
- append-only event persistence
- next-sequence allocation for turns, tools, and events
- diagnostics summary queries for agent runs

This store is one of the most important persistence surfaces in the current scaffold.

## Persistence Philosophy

The current backend tries to preserve operationally meaningful state, not just product data.

That means persistence is used heavily for:
- agent run lifecycle state
- turn lifecycle state
- tool-call state
- event history
- task snapshots
- error summaries

This aligns with the scaffold's operational-first philosophy.

## SQLite Vs Postgres Behavior

The runtime deliberately treats SQLite and Postgres differently in some cases.

### Postgres
Postgres is the primary development and production persistence target.

It is the default database shape in the backend README and migration workflow.

### SQLite
SQLite is primarily used for fast local tests and scaffold validation.

Important special behavior:
- when the configured database URL starts with `sqlite+aiosqlite`, the app container uses `InMemoryAgentStore`
- otherwise it uses `SqlAlchemyAgentStore`

That means SQLite-backed test paths are not necessarily exercising the exact same agent persistence path as non-SQLite runtime environments.

This is intentional for speed, but it matters when evaluating test coverage and runtime confidence.

## Migrations

Migration workflow is managed through Alembic.

Relevant files:
- `backend/alembic.ini`
- `backend/alembic/`

Common commands from `backend/`:
- `make migrate`
- `make revision message="add task table"`

## Operational DB Checks

The backend performs DB checks in a few important places.

### Startup
In startup:
- non-SQLite DBs are pinged during bootstrap
- failure is treated as a startup failure

### Readiness
In readiness:
- non-SQLite DBs are pinged again
- failure becomes a structured dependency readiness error

This means DB reachability is treated as an operational truth boundary.

## What To Keep In Mind When Extending Persistence

High-signal rules of thumb for this codebase:
- preserve structured failure state, not just success data
- prefer explicit runtime seams over route-level DB usage
- preserve ordered event semantics where ordering matters
- understand whether a test path is exercising in-memory or SQLAlchemy-backed state
- update docs when persistence behavior materially changes

## Where To Read In Code

High-signal files:
- `platform/composition/app_container.py`
- `platform/db/engine.py`
- `platform/db/session.py`
- `platform/db/repositories.py`
- `platform/db/uow.py`
- `platform/db/models.py`
- `alembic/`
