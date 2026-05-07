# Error Handling Contract

## Purpose
This contract defines how the application must behave operationally under failure.

It governs:
- error taxonomy
- canonical error shape
- code design and translation rules
- startup and readiness failure behavior
- transport, background, provider, and persistence failure handling
- redaction and anti-silent-failure rules

Use [architecture.md](/home/antonioborgerees/coding/HelloSales/product-ops/operational-contract/architecture.md) for structural rules.

Use [observability.md](/home/antonioborgerees/coding/HelloSales/product-ops/operational-contract/observability.md) for signal and diagnostics rules.

Use [testing.md](/home/antonioborgerees/coding/HelloSales/product-ops/operational-contract/testing.md) for verification requirements.

Implementation anchors and scaffold-specific runtime locations belong in docs, not in this contract.

## Scope
This contract applies when a change:
- introduces or changes a failure path
- translates one error across a boundary
- changes startup, readiness, or transport error behavior
- changes background, workflow, provider, or persistence failure handling
- changes logging, event emission, or redaction around failures

## How To Use This Contract
Use this contract to determine:
- what failure category and code rules apply
- what error detail must be preserved
- what behaviors are forbidden because they hide or distort failure
- what review evidence should exist for failure-handling conformance

## Requirement Index

| ID | Title | Applies To | Severity If Violated |
| --- | --- | --- | --- |
| ERR-CORE-001 | No failure may disappear | all failure paths | Blocker |
| ERR-SHAPE-001 | Operational errors must preserve the canonical shape | structured errors and translations | High |
| ERR-CODE-001 | Error codes must be stable and machine-usable | error code design | High |
| ERR-TRANS-001 | Error translation must preserve cause and context | cross-layer translation | High |
| ERR-RETRY-001 | Retryable errors must be retried through explicit bounded policy | retryable failure paths | High |
| ERR-STARTUP-001 | Known-fatal startup failures must fail before traffic | startup and readiness | Blocker |
| ERR-HTTP-001 | Transport adapters must preserve the operational signal | API and HTTP boundaries | High |
| ERR-BG-001 | Background work must end in explicit inspectable failure state | task runners and background jobs | Blocker |
| ERR-PROVIDER-001 | Provider failures must remain classified and observable | external provider paths | High |
| ERR-DATA-001 | Persistence and data failures must be loud and distinct | DB and storage behavior | High |
| ERR-REDACT-001 | Redaction must protect secrets without destroying diagnosis | error detail payloads | High |

## Core Principles

1. No failure may disappear.
2. Every failure must be attributable, classifiable, and inspectable.
3. Errors must preserve full machine-readable detail except explicitly redacted secrets.
4. Unknown failure is a defect in observability, not an acceptable state.
5. Startup misconfiguration must stop the process before traffic is accepted.
6. Background work must surface success or failure explicitly.
7. Health signals must reflect operational truth, not optimistic guesses.
8. Retrying is allowed only when the failure is understood, bounded, and observable.

## Taxonomy

Every emitted error code must belong to a stable category. The canonical categories are:
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

Choose the narrowest truthful category.
Do not collapse distinct operational failures into one generic category.

## Requirements

### ERR-CORE-001: No Failure May Disappear

**Rule**
Every failure path must remain visible, attributable, and terminally meaningful to at least one caller, operator, or scheduler surface.

**Required**
- emit a structured failure signal
- include a stable code, component, and operation
- preserve enough redacted detail for diagnosis
- produce an explicit state transition or caller-visible failure result

**Forbidden**
- catching and doing nothing
- returning `None`, `False`, or an empty collection to hide operational failure
- logging and continuing as if the operation succeeded
- launching asynchronous work without ownership and terminal-state reporting

**Evidence**
- failure paths end in explicit failed, cancelled, timed out, or partial-failure outcomes where applicable
- review can point to the emitted failure signal and the affected terminal state

### ERR-SHAPE-001: Operational Errors Must Preserve The Canonical Shape

**Rule**
Every operational error must be representable as a structured object with stable machine-usable fields.

**Required fields**
- `code`
- `category`
- `message`
- `details`
- `severity`
- `retryable`
- `operation`
- `component`
- `correlation_id`
- `trace_id` when available
- `cause`
- `causes` when meaningful
- `timestamp`

**Required**
- preserve useful detail such as identifiers, resource names, timeout values, retry counters, remote status codes, remote payload fragments, and relevant state snapshot
- normalize non-serializable values instead of dropping them silently

**Forbidden**
- opaque or underspecified production error shapes
- dropping useful detail because it is inconvenient to serialize

**Evidence**
- structured errors and transport responses expose the canonical fields or a justified safe subset

### ERR-CODE-001: Error Codes Must Be Stable And Machine-Usable

**Rule**
Error codes must be stable across refactors and useful for alerting, metrics, and review.

**Required**
- use short machine-readable codes
- prefer `{category}.{reason}` or `{category}.{subsystem}.{reason}`
- keep codes specific enough to distinguish materially different failure classes

**Forbidden**
- free-form sentences as codes
- exception class names as codes
- one catch-all code for unrelated failures

**Evidence**
- emitted codes are stable and category-aligned
- operators and review can distinguish major failure classes from codes alone

### ERR-TRANS-001: Error Translation Must Preserve Cause And Context

**Rule**
When translating an error across layers, preserve the original cause and enrich rather than erase it.

**Required**
- keep the original cause or causal chain
- keep the original code when possible
- add layer-specific context such as operation, component, transport mapping, or identifiers
- preserve stack or remote diagnostics for unexpected failures

**Forbidden**
- replacing a specific provider timeout with generic `operation_failed`
- dropping causal chain information
- hiding a dependency outage behind an empty successful response

**Evidence**
- translated errors still expose the originating failure meaningfully
- review can trace a boundary error back to its cause

### ERR-RETRY-001: Retryable Errors Must Be Retried Through Explicit Bounded Policy

**Rule**
An error marked `retryable=true` must be retried by the owning runtime when a retry can be performed safely, and must not be retried when doing so would violate idempotency, corrupt user-visible output, exceed a configured budget, or hide terminal failure.

**Required**
- define the retry owner for each retryable failure path
- retry through an explicit bounded policy with a configured attempt budget
- classify retryable and non-retryable failures before retry decisions are made
- preserve attempt number, maximum attempts, next attempt when applicable, issue kind, issue code, and retryable status in structured state or events
- stop retrying when the budget is exhausted and expose the final failure as terminal state
- preserve the original cause and the last retry issue on retry exhaustion
- make fallback or backup-provider selection explicit when it is part of retry behavior

**Appropriate retry behavior**
- retry transient provider, dependency, timeout, rate-limit, and remote 5xx failures only when the operation is safe to repeat
- respect idempotency and side-effect boundaries; non-idempotent operations require an explicit idempotency key, dedupe strategy, or no retry
- do not retry after a partial externally visible result has been emitted unless the runtime can prove replay is safe
- use corrective retry prompts only for LLM output-shape or validation failures where prompt correction is the designed recovery path
- keep cancellation terminal and distinct from retry exhaustion

**Forbidden**
- marking an error `retryable=true` with no owning retry policy
- adding hidden retry loops with no cap, no emitted retry event, or no terminal exhaustion behavior
- retrying authentication, authorization, validation, domain, or caller errors unless a specific contract marks the failure as recoverable
- converting retry exhaustion into successful empty output or a generic internal error
- retrying non-idempotent side effects by default

**Evidence**
- retryable paths show a bounded decision point and emitted retry/exhaustion signal
- terminal failure records preserve the final code, cause, retry budget, and last attempt detail

### ERR-STARTUP-001: Known-Fatal Startup Failures Must Fail Before Traffic

**Rule**
The system must fail before serving traffic when a required dependency or required startup check is not usable.

**Required**
- validate startup prerequisites explicitly
- abort startup on required capability failure
- keep readiness failed until safe operation is possible
- emit the exact failing code and context

**Examples of required checks**
- settings parse and validation
- required secret presence
- mandatory persistence connectivity
- migration compatibility or explicit migration strategy check
- required provider configuration sanity
- workflow and module registry assembly

**Forbidden**
- deferring known-fatal startup failure until the first request
- declaring readiness while a required dependency is unavailable

**Evidence**
- startup checks fail loudly and deterministically
- readiness reflects required dependency state

### ERR-HTTP-001: Transport Adapters Must Preserve The Operational Signal

**Rule**
Transport adapters must preserve the operational meaning of structured failures rather than flattening them into ambiguous responses.

**Required**
- map structured application errors to structured responses
- preserve stable code and useful details payload at the safe exposure level
- preserve correlation identifiers in responses when safe
- distinguish caller errors from service or operator-visible failures

**Forbidden**
- silent generic success or empty `200` responses on unknown exceptions
- stripping useful error detail without redaction or exposure justification

**Evidence**
- transport responses preserve the structured error signal
- full redacted internal detail remains available when external exposure must be reduced

### ERR-BG-001: Background Work Must End In Explicit Inspectable Failure State

**Rule**
Every background task must have explicit ownership, lifecycle state, and inspectable failure detail.

**Required**
- preserve task identity, submitted time, started time, terminal time, status, and retry count
- preserve stable code and structured error details on failure
- reconcile orphaned tasks into explicit failed or timed-out state

**Forbidden**
- fire-and-forget work with no owner or task id
- in-memory-only tracking for important work
- failures that exist only in worker stdout or logs
- ambiguous terminal statuses such as `done` with no precise mapping

**Evidence**
- task state is inspectable through runtime surfaces
- failure records preserve terminal details and codes

### ERR-PROVIDER-001: Provider Failures Must Remain Classified And Observable

**Rule**
External provider failures must preserve remote context, retry semantics, and clear classification.

**Required**
- define timeout, retry policy, idempotency stance, normalized error mapping, and observability boundary for provider calls
- capture remote status code, provider request id, rate-limit headers, timeout configuration, model or endpoint name, and normalized remote error payload when available
- classify provider failures with specific subcodes where possible

**Forbidden**
- retrying non-idempotent calls by default
- collapsing all provider failures into one generic code
- discarding remote identifiers needed for escalation or diagnosis

**Evidence**
- provider-backed failure paths preserve normalized remote context
- retries and retry exhaustion are explicit and inspectable

### ERR-DATA-001: Persistence And Data Failures Must Be Loud And Distinct

**Rule**
Persistence, serialization, and data-shape failures must be classified distinctly and must not be confused with ordinary missing-data behavior.

**Required**
- map connectivity, timeout, integrity, serialization, and schema-shape failures separately
- include entity ids and transaction context where possible
- fail writes explicitly if persistence confirmation is missing

**Forbidden**
- assuming write success without checking the result
- treating missing rows and storage outage as the same error
- swallowing commit failures and returning success

**Evidence**
- storage failures preserve distinct code and context
- review can distinguish not-found behavior from storage outage behavior

### ERR-REDACT-001: Redaction Must Protect Secrets Without Destroying Diagnosis

**Rule**
Error detail must be redacted explicitly and deterministically, not erased wholesale.

**Always redact**
- API keys
- access tokens
- cookies
- passwords
- raw authorization headers
- private signing material
- full card or bank data
- other secret or regulated material

**Required**
- prefer redacted full context over truncated context
- keep the diagnostic structure intact after redaction

**Forbidden**
- leaking secret material into details payloads
- solving exposure risk by dropping the entire detail payload when narrower redaction would work

**Evidence**
- secret-bearing fields are redacted deterministically
- redacted error detail still supports debugging and review

## Review Rejection Criteria
Reject a change if it:
- adds a catch path that can swallow a failure
- introduces a new background path with no durable terminal status
- allows a startup dependency to fail after readiness is declared
- drops useful error detail without redaction justification
- adds a retry loop with no cap or no visibility
- adds an invisible fallback path
- makes a dependency outage indistinguishable from empty successful output
- collapses a specific failure into an uninformative generic code

## Related Docs
- [errors-and-logging.md](/home/antonioborgerees/coding/HelloSales/backend/docs/errors-and-logging.md)
- [testing-and-operations.md](/home/antonioborgerees/coding/HelloSales/backend/docs/testing-and-operations.md)
