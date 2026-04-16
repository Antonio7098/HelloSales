# Errors And Logging

## Purpose
This document explains the implemented philosophy behind errors, logging, and operational failure handling in the backend.

For normative rules, taxonomy requirements, and review criteria, use:
- `ops/operational-contract/errors.md`
- `ops/operational-contract/observability.md`

This document explains how to think about the current backend implementation and what the current runtime is trying to preserve.

## Core Philosophy

The backend treats failures as operational facts that must remain visible.

The core ideas are:
- failures should not disappear
- errors should remain machine-usable
- logging should be structured
- background and agent failures should remain inspectable after the fact
- readiness and startup should reflect operational truth
- redaction should protect secrets without destroying diagnosis

## Error Taxonomy Philosophy

The error taxonomy is intended to answer two questions quickly:
- what kind of failure happened?
- what should the operator or caller infer from it?

The backend uses categories such as:
- `config`
- `startup`
- `validation`
- `domain`
- `dependency`
- `provider`
- `timeout`
- `concurrency`
- `data`
- `workflow`
- `background`
- `internal`

The philosophy is to choose the narrowest truthful category.
A broad generic category makes operations and review weaker.

## Error Shape Philosophy

The backend wants operational errors to stay structured rather than devolving into message-only exceptions.

That means errors should preserve fields like:
- code
- category
- severity
- retryability
- operation
- component
- correlation identifiers
- details payload
- cause / causal chain where relevant

The important point is not just consistency.
It is that a failure should remain:
- diagnosable
- searchable
- suitable for alerts and metrics
- traceable across boundaries

## Logging Philosophy

Logging is treated as a structured operational signal, not a prose diary.

Good logging in this backend should:
- use stable event names
- include machine-usable fields
- preserve correlation ids
- carry enough context to diagnose the failure
- distinguish failure, degradation, and success truthfully

Bad logging in this backend would be:
- message-only logging
- logging an exception without context
- logging success after degraded behavior or partial failure
- using prose instead of stable codes for operator-critical meaning

## Operational Events And Alerts

The backend has a separate operational event surface beyond ordinary logs.

Location:
- `platform/observability/runtime.py`

This runtime keeps:
- recent operational events
- active alerts derived from event severity and code

The important philosophy is that logs and operational events are complementary.
The system should not rely on only one of them for important failure visibility.

## Startup Failure Philosophy

Startup is treated as a truth boundary.

If the system knows it cannot safely run, it should fail before serving traffic.

That is why startup currently validates:
- environment validity
- provider configuration shape
- database reachability when required

Startup completion and startup failure are both emitted as operational signals.

## Background Task Failure Philosophy

Background work is not allowed to disappear into untracked async execution.

The task runner preserves:
- task identity
- task lifecycle state
- task error summary
- structured failure details
- operational failure event emission

The point is that once a task fails, an operator should be able to inspect that failure through runtime state rather than searching only through loose logs.

## Agent Failure Philosophy

The agent runtime preserves multiple layers of failure visibility:
- tool-call-level failure state
- turn-level failure state
- run-level failure state
- append-only stream events
- operational events for run-level failure

This is stronger than a normal request-response path because agent execution is long-lived and multi-step.

## Provider Failure Philosophy

Provider failures are treated as a meaningful operational class, not just generic request errors.

The system tries to preserve:
- provider-specific codes
- remote identifiers when available
- lifecycle context
- timeout/retry context
- stable failure meaning across runtime boundaries

This matters because provider-backed paths are one of the most important parts of the current scaffold.

## Redaction Philosophy

The backend wants to preserve full useful context while still protecting secrets.

The philosophy is:
- redact specific secret-bearing fields
- keep the rest of the structure
- do not delete the entire error payload if narrower redaction will work

That keeps failures diagnosable without exposing sensitive material.

## How To Read The Current Implementation

High-signal files:
- `shared/errors.py`
- `entrypoints/http/error_handlers.py`
- `platform/observability/runtime.py`
- `platform/observability/middleware.py`
- `platform/tasks/runner.py`
- `platform/composition/startup.py`
- `platform/agents/runtime.py`

## What Still May Need Documentation Later

As the backend grows, it may be worth adding dedicated docs for:
- persistence model and SQLAlchemy store behavior
- configuration model and environment variables in more depth
- event stream / SSE behavior in more depth
- migration workflow and operational DB lifecycle
