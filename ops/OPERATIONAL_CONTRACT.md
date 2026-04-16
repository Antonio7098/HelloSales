# Operational Contract

## Purpose
This document defines how the application must behave operationally under failure.

It governs:
- error taxonomy
- error payload shape
- logging and event emission
- startup and readiness behavior
- background execution failure handling
- external integration failure handling
- rules for avoiding silent failures
- fail-fast and fail-loud policy

Use this document as the operational source of truth while the system is still being scaffolded.
Use [ARCHITECTURE_RULES.md](/home/antonioborgerees/coding/HelloSales/ops/ARCHITECTURE_RULES.md) for code structure and dependency rules.

## Core Principles

1. No failure may disappear.
2. Every failure must be attributable, classifiable, and inspectable.
3. Errors must preserve full machine-readable detail, except explicitly redacted secrets.
4. Unknown failure is a defect in observability, not an acceptable state.
5. Startup misconfiguration must stop the process before traffic is accepted.
6. Background work must surface success or failure explicitly.
7. Health signals must reflect operational truth, not optimistic guesses.
8. Retrying is allowed only when the failure is understood, bounded, and observable.

## Operational Defaults

Unless a narrower rule overrides it, every failure path must:
- emit a structured log event
- include a stable error code
- include the failing subsystem and operation
- include correlation identifiers
- include the original exception class
- include the original exception message
- preserve causal chain information
- include redacted diagnostic details sufficient for debugging
- produce a detectable state transition for the caller, operator, or scheduler

There is no approved pattern where code catches an exception and does nothing.
There is no approved pattern where code returns `None`, `False`, or an empty collection to hide operational failure.
There is no approved pattern where asynchronous work is launched without ownership, visibility, and terminal-state reporting.

## Canonical Error Shape

Every operational error must be representable as a structured object with at least:
- `code`: stable machine-readable code such as `provider.timeout`
- `category`: taxonomy category from this document
- `message`: short human-readable summary
- `details`: structured diagnostics payload
- `severity`: `info`, `warning`, `error`, or `critical`
- `retryable`: boolean
- `operation`: logical operation name such as `lead.enrich` or `postgres.connect`
- `component`: owning subsystem such as `http`, `workflow`, `db`, `provider`, `scheduler`
- `correlation_id`: request, job, or workflow correlation id
- `trace_id`: tracing id when available
- `cause`: normalized representation of the immediate cause
- `causes`: optional causal chain for wrapped failures
- `timestamp`: UTC timestamp at emission time

`details` must preserve the full useful context for debugging:
- input identifiers and object ids
- target resource names
- timeout values
- retry counters
- remote status codes
- remote error payloads
- state snapshot relevant to the failure
- environment flags that affect behavior

`details` must not silently omit relevant fields because they are inconvenient to serialize.
If a field cannot be serialized directly, normalize it into a string or structured subset and keep it.

## Current Scaffold Conventions

The following conventions are not aspirational. They are already present in the backend scaffold and future work must extend them rather than invent parallel patterns.

Current implementation anchors:
- structured application errors live in [backend/src/hello_sales_backend/shared/errors.py](/home/antonioborgerees/coding/HelloSales/backend/src/hello_sales_backend/shared/errors.py)
- HTTP error mapping lives in [backend/src/hello_sales_backend/entrypoints/http/error_handlers.py](/home/antonioborgerees/coding/HelloSales/backend/src/hello_sales_backend/entrypoints/http/error_handlers.py)
- HTTP request correlation middleware lives in [backend/src/hello_sales_backend/platform/observability/middleware.py](/home/antonioborgerees/coding/HelloSales/backend/src/hello_sales_backend/platform/observability/middleware.py)
- startup validation and startup event emission live in [backend/src/hello_sales_backend/platform/composition/startup.py](/home/antonioborgerees/coding/HelloSales/backend/src/hello_sales_backend/platform/composition/startup.py)
- health and readiness logic live in [backend/src/hello_sales_backend/platform/observability/health.py](/home/antonioborgerees/coding/HelloSales/backend/src/hello_sales_backend/platform/observability/health.py)
- operational event and alert runtime lives in [backend/src/hello_sales_backend/platform/observability/runtime.py](/home/antonioborgerees/coding/HelloSales/backend/src/hello_sales_backend/platform/observability/runtime.py)
- background task state and failure capture live in [backend/src/hello_sales_backend/platform/tasks/runner.py](/home/antonioborgerees/coding/HelloSales/backend/src/hello_sales_backend/platform/tasks/runner.py) and [backend/src/hello_sales_backend/platform/tasks/models.py](/home/antonioborgerees/coding/HelloSales/backend/src/hello_sales_backend/platform/tasks/models.py)
- diagnostics exposure lives in [backend/src/hello_sales_backend/modules/system/use_cases/system_service.py](/home/antonioborgerees/coding/HelloSales/backend/src/hello_sales_backend/modules/system/use_cases/system_service.py)

Future additions must reuse these anchors unless there is a strong architectural reason to replace them.

### Error Construction Rule
New operational errors should be created through the shared error helpers, not ad hoc exception shapes.

Required:
- use `app_error(...)` for new structured application errors
- use `internal_error(...)` for unexpected defects translated at system boundaries
- use `orchestration_error(...)` for workflow-runtime failures

Not allowed:
- inventing a second application error base class
- raising raw vendor exceptions across module or transport boundaries when a stable application code should exist
- creating opaque `Exception("something failed")` placeholders in production paths

### Request Correlation Rule
HTTP request handling already binds and returns:
- `x-request-id`
- `x-trace-id`
- `x-correlation-id`

Future HTTP code must:
- preserve these identifiers through downstream calls where safe
- include them in emitted errors and events
- avoid generating alternate per-layer correlation keys for the same request path

### Runtime Event Rule
The scaffold already emits operational events for:
- startup completion
- startup failure
- request failure
- unexpected request failure
- background task failure

Future failure paths must also emit operational events through the shared observability runtime.

Required event fields:
- `event_type`
- `severity`
- `component`
- `operation`
- `code`
- `correlation_id` when available
- `trace_id` when available
- structured `payload`

If a new component can fail meaningfully and does not emit events, that component is incomplete.

### Alert Rule
The current scaffold derives alerts from high-severity operational events.

This means:
- `error` and `critical` event severities are alert-producing by default
- event codes must be stable enough to act as alert identifiers
- future alert-policy changes must remain code-driven and machine-readable

Do not build alerting around free-form log text matching.

### Background Task Rule
Background task snapshots already preserve:
- task lifecycle status
- correlation identifiers
- error type and message
- error code
- error category
- structured error details

Future task or worker code must preserve this shape.

Not allowed:
- recording only a terminal boolean
- losing the stable code once an exception crosses the task boundary
- emitting task failure only to stdout or logs

### Diagnostics Rule
`/api/system/diagnostics` is the canonical operator-facing scaffold endpoint for in-process observability.

It currently exposes:
- provider availability
- task summary and recent task snapshots
- recent operational events
- active alerts

Future additions that introduce operational state should either:
- extend this diagnostics surface, or
- justify why a separate diagnostics surface is required

Do not create scattered hidden debug endpoints for each subsystem.

### Health Semantics Rule
The scaffold already distinguishes:
- `live`
- `ready`
- `degraded`

Future health changes must preserve these meanings:
- `live`: process is up
- `ready`: process can safely serve its intended workload
- `degraded`: process is up but a non-required capability is impaired

Do not collapse these states back into a single optimistic `ok`.

## Redaction Rule

Full details means full operational detail, not unrestricted secret leakage.

Always redact:
- API keys
- access tokens
- cookies
- passwords
- raw authorization headers
- private signing material
- full card or bank data
- other regulated or secret material

Redaction must be explicit and deterministic.
The system must prefer redacted full context over truncated context.
Do not solve secret exposure risk by dropping the entire error detail payload.

## Error Taxonomy

Every emitted error code must belong to one of these categories.

### 1. `config`
Use for invalid or missing configuration, environment, feature-flag, or bootstrap inputs.

Examples:
- missing required environment variable
- malformed DSN
- invalid deployment mode
- incompatible feature combination

Default behavior:
- fail startup immediately
- mark readiness as failed
- do not accept traffic

### 2. `startup`
Use for failures during process boot, dependency wiring, migration checks, registry loading, or provider initialization.

Examples:
- container assembly failure
- module bootstrap failure
- migration state mismatch
- provider client creation failure

Default behavior:
- fail startup immediately
- log at `critical` when the process cannot safely run

### 3. `validation`
Use for invalid caller input or contract violations at system boundaries.

Examples:
- malformed request payload
- missing required domain field
- invalid command parameters

Default behavior:
- reject fast
- return deterministic caller-visible error
- do not retry

### 4. `domain`
Use for business-rule violations and expected invariant enforcement.

Examples:
- illegal state transition
- duplicate operation not allowed by business rules
- forbidden action due to workflow state

Default behavior:
- reject deterministically
- keep detailed business context
- do not downgrade to generic validation error

### 5. `dependency`
Use for failures in required infrastructure dependencies.

Examples:
- database unavailable
- Redis unavailable
- queue broker unavailable
- storage backend unavailable

Default behavior:
- fail the operation loudly
- degrade readiness if the dependency is required
- retry only if the call is explicitly retry-safe

### 6. `provider`
Use for third-party API and external service failures.

Examples:
- timeout
- rate limit
- transport reset
- malformed provider response
- remote 5xx
- remote authentication failure

Default behavior:
- classify further with subcodes such as `provider.timeout` or `provider.rate_limit`
- preserve remote response metadata
- retry only with explicit policy and observability

### 7. `timeout`
Use when an operation exceeds a defined deadline, whether local or remote.

Examples:
- DB query deadline exceeded
- workflow step timeout
- outbound HTTP timeout

Default behavior:
- include configured timeout and elapsed duration
- cancel downstream work if possible
- emit explicit timeout code rather than generic failure

### 8. `concurrency`
Use for races, lock contention, duplicate delivery, idempotency conflicts, and optimistic write conflicts.

Examples:
- version mismatch
- task already running
- duplicate event delivery
- deadlock detected

Default behavior:
- make the concurrency semantics explicit
- mark retryability deliberately, not implicitly

### 9. `data`
Use for persistence corruption, serialization faults, schema mismatch, and unexpected null or shape violations in stored or retrieved data.

Examples:
- invariant broken in persisted record
- deserialization failure
- missing required column in runtime path
- impossible enum value from storage

Default behavior:
- treat as operational defect
- include record identifiers and schema context
- escalate severity above normal caller error

### 10. `workflow`
Use for orchestration failures across multiple steps or systems.

Examples:
- compensation failure
- partial completion with inconsistent state
- exceeded retry budget
- step dependency missing

Default behavior:
- persist workflow state and terminal outcome
- never leave status ambiguous
- include step-level failure detail

### 11. `background`
Use for async tasks, scheduled jobs, fire-and-forget work, and worker-process failures.

Examples:
- task runner crash
- dropped task
- unhandled job exception
- result persistence failure

Default behavior:
- persist task state
- emit terminal failure event
- never rely on logs alone as the only failure signal

### 12. `internal`
Use for uncaught defects, impossible branches, and programming errors.

Examples:
- unhandled exception
- impossible state reached
- missing case in dispatcher
- invariant broken by code defect

Default behavior:
- fail loud
- preserve stack trace and causal chain
- do not remap to a misleading business or validation code

## Code Design Rules

### Stable Code Policy
Each error code must be:
- stable across refactors
- short and machine-readable
- specific enough for alerting and metrics
- independent from human wording

Preferred format:
- `{category}.{reason}`
- `{category}.{subsystem}.{reason}` when more precision is needed

Examples:
- `config.missing_env`
- `startup.module_bootstrap_failed`
- `provider.openai.timeout`
- `dependency.postgres.unavailable`
- `workflow.retry_budget_exhausted`
- `background.task_crashed`
- `internal.unhandled_exception`

Do not use:
- free-form sentences as codes
- exception class names as codes
- one catch-all code for unrelated failures

### Wrapping Rule
When translating one error into another layer:
- keep the original cause
- keep the original code when possible
- add layer-specific context
- do not discard stack or remote diagnostics

Allowed:
- adding `operation`, `component`, and business identifiers
- changing transport status mapping
- normalizing vendor-specific payloads

Not allowed:
- replacing a specific provider timeout with generic `operation_failed`
- dropping causal chain information
- hiding a dependency outage behind an empty successful response

## Fail Fast Policy

The system must fail before serving traffic when any required dependency for safe operation is not usable.

Required startup checks:
- settings parse and validation
- required secret presence
- database connectivity for mandatory persistence paths
- migration compatibility or explicit migration strategy check
- required provider configuration sanity
- workflow and module registry assembly
- logger and telemetry initialization

Current scaffold note:
- startup validation already rejects invalid environment configuration and partial LLM provider configuration
- startup already emits success and failure events through the observability runtime

Future startup checks should follow the same pattern:
- validate explicitly
- emit a structured startup event
- abort startup on required capability failure

If any required startup check fails:
- process exits non-zero or startup returns failure
- readiness endpoint remains failed
- log at `critical`
- emit the exact failing code and context

Do not defer known-fatal startup errors until first request.

## Fail Loud Policy

At runtime, every failure must be visible in at least one immediate channel and one durable channel.

Immediate channels:
- request response
- worker terminal status
- scheduler run result
- metrics and alerting event
- stderr or structured runtime log

Durable channels:
- persisted task record
- durable event sink
- centralized log store
- tracing backend

Current scaffold note:
- the event/alert channel is currently implemented as an in-memory operational runtime for scaffold-stage visibility
- task snapshots are persisted when a non-SQLite task event sink is configured

This is acceptable for scaffold stage, but future production-facing work should add a durable operational event sink instead of relying on in-memory retention alone.

A failure is still silent if it only appears in one place operators are unlikely to inspect.

## Anti-Silent-Failure Rules

### 1. No Broad Catch Without Re-Emission
If code catches `Exception`, it must immediately do one of:
- translate into a richer structured error and raise
- mark the operation failed and re-raise
- emit a terminal failure record and return an explicit failed result

It must never:
- `pass`
- log and continue as success
- downgrade to empty output

### 2. No Fire-And-Forget Without Ownership
Any spawned background work must have:
- an owner
- a task id
- input context
- a timeout
- a retry policy or explicit no-retry decision
- terminal success or failure recording

Untracked background tasks are prohibited.

### 3. No Hidden Fallbacks
Fallback behavior must be explicit and observable.

Allowed:
- fallback to noop provider in local development if configured and logged
- fallback to cached data if staleness is reported

Not allowed:
- silently switching provider implementations
- silently dropping writes
- silently skipping a failed workflow step

### 4. No Ambiguous Success States
Every operation must end in one of:
- succeeded
- failed
- cancelled
- timed_out
- partial_failure

States such as `done`, `processed`, or missing status are not precise enough unless they map directly to one of the above.

### 5. No Infinite Retries
Every retry loop must declare:
- retryable conditions
- max attempts
- backoff policy
- timeout budget
- emitted retry events

Retry exhaustion must emit a distinct terminal code.

### 6. No Empty Exception Translation
When translating low-level exceptions, include:
- original exception type
- original message
- operation context
- identifiers required to replay or inspect the failure

Generic messages like `request failed` are not sufficient on their own.

### 7. No Readiness Lies
Health endpoints must distinguish:
- liveness: process is running
- readiness: process can safely serve traffic
- degraded: process is running with impaired but non-fatal dependencies

Readiness must fail when required dependencies are down.
Do not return healthy just because the web server process is alive.

## Logging Rules

All operational logs must be structured and queryable.

Every error log must include:
- `event`
- `code`
- `category`
- `severity`
- `component`
- `operation`
- `correlation_id`
- `trace_id` when available
- `retryable`
- `details`
- exception stack information for unexpected failures

Recommended event names:
- `startup_failed`
- `dependency_check_failed`
- `request_failed`
- `workflow_step_failed`
- `background_task_failed`
- `provider_call_failed`
- `retry_scheduled`
- `retry_exhausted`

Avoid:
- string-only logs with missing fields
- logging an exception message without context
- emitting success logs when the operation actually degraded or partially failed

Logging and event emission are complementary, not interchangeable.
If a new failure path only logs and does not emit an operational event or terminal state transition, it is still under-instrumented.

## HTTP and API Rules

Transport adapters must preserve the operational signal.

Required:
- map structured application errors to structured responses
- return the stable code and details payload
- preserve correlation ids in responses when safe
- distinguish caller errors from service/operator errors

Default response shape should include:
- `code`
- `message`
- `details`
- `correlation_id`

Current scaffold note:
- HTTP error responses also include category, severity, retryability, operation, component, trace identifiers, cause, causes, and timestamp

Future transport adapters should preserve this richness unless a narrower external exposure rule explicitly requires reduction.
If details are reduced externally, full redacted details must still be emitted internally.

Unknown exceptions must not produce silent generic success or empty 200 responses.
If external exposure must be reduced for security reasons, the system still must log and persist the full redacted details internally.

## Background Job Rules

Every background task must persist or expose:
- task id
- submitted time
- started time
- terminal time
- status
- retry count
- error code on failure
- structured error details on failure

If a worker crashes mid-task, the system must reconcile orphaned tasks into an explicit failed or timed out state.

Do not accept:
- in-memory-only task tracking for important work
- exceptions that only appear in worker stdout
- tasks whose caller cannot inspect terminal failure details

Current scaffold note:
- the in-process runner already emits both task snapshots and operational events for failures
- terminal task failure detail already includes stable code and structured payload

Future async execution systems must preserve at least that level of detail.

## External Provider Rules

Every provider call must define:
- timeout
- retry policy
- idempotency stance
- normalized error mapping
- request and response observability boundaries

Capture and preserve when available:
- remote status code
- provider request id
- rate-limit headers
- timeout configuration
- model or endpoint name
- normalized remote error payload

Never:
- retry non-idempotent calls by default
- collapse all provider failures into one generic code
- discard remote identifiers needed for support escalation

## Persistence and Data Rules

Database and storage failures must be loud and classified.

Required:
- map connectivity, timeout, integrity, and serialization failures separately
- include entity ids and transaction context where possible
- fail writes explicitly if persistence confirmation is missing

Not allowed:
- assuming write success without checking the result
- treating missing rows and storage outage as the same error
- swallowing commit failures and returning success

## Metrics and Alerting Rules

Metrics must support detection of hidden failure patterns.

At minimum emit counters or events for:
- failures by `code`
- retries by `code`
- timeout count
- startup failure count
- background task terminal failures
- dependency health transitions
- degraded mode entry and exit

Alerts should be driven by:
- high-severity error codes
- retry exhaustion
- startup failure
- sustained dependency failure
- elevated unknown internal failures

Current scaffold note:
- a minimal alert policy already exists in the observability runtime and is severity/code-driven
- metrics counters are not yet implemented as first-class code

Future metrics work should use the same stable codes already emitted by errors and operational events.

## Review Checklist

Reject a change if any of the following is true:
- a catch block can swallow a failure
- a new background path has no durable terminal status
- a startup dependency can fail after readiness is declared
- an error response drops useful detail without redaction justification
- a retry loop has no cap or no visibility
- a fallback path is invisible to operators
- a dependency outage can be mistaken for empty successful output
- a specific failure is collapsed into an uninformative generic code

## Scaffold-Now Recommendations

While the full product brief is still unknown, the scaffold should be built with these defaults:
- a single `AppError` base type that carries the canonical fields in this document
- explicit category constants and code registry conventions
- one central error-to-log and error-to-response mapper
- startup validation that can abort process boot
- request correlation middleware
- background task records with terminal failure payloads
- structured logging with exception and cause support
- explicit health model with `live`, `ready`, and `degraded`
- redaction helpers applied before emission

This is the minimum acceptable baseline for avoiding silent failure debt early.

## Extension Rules For Future Work

When adding a new provider, workflow, job, queue consumer, cron task, or transport adapter:

1. Define the expected failure classes before implementing the happy path.
2. Assign stable error codes before wiring retries.
3. Decide which failures are caller-visible, operator-visible, and both.
4. Emit operational events from the same place the failure is classified.
5. Ensure diagnostics can expose the component's latest relevant operational state.
6. Add tests for at least one explicit expected failure and one unexpected failure.

When reviewing future code, reject additions that:
- bypass the shared error helpers
- invent a private event or alert shape
- drop correlation ids at subsystem boundaries
- log failures without an event or terminal state update
- add fallback logic that operators cannot see in diagnostics
