# Sprint Reasoning: Observability Foundation

> Project: HelloSales
> Sprint ID: sprint-01-observability-foundation
> Output: `ops/sprints/sprint-01-observability-foundation/reasoning.md`

## Overview

**Sprint:** Observability Foundation
**Purpose:** Introduce scaffold-stage monitoring, telemetry, and metrics infrastructure that fits the current backend architecture and observability contracts.
**Tracker:** `ops/sprints/sprint-01-observability-foundation/tracker.md`
**Depends On:** None

## Requirement Map

### Requirement Index Used In This Sprint

| Requirement ID | Title | Area | Applicability | Why It Matters For This Sprint |
| --- | --- | --- | --- | --- |
| PRE-SCOPE-001 | Foundation work may proceed before the brief | Pre-Brief Scope | Applicable | Logging, tracing, middleware, diagnostics, and health are explicitly safe scaffold-stage work. |
| PRE-SCOPE-003 | Operational scaffolding should be favored over product assumptions | Pre-Brief Scope | Applicable | The sprint must remain operational and generic, not product-specific. |
| PRE-SCOPE-004 | Public APIs must remain intentionally narrow before the brief | Pre-Brief Scope | Applicable | Any metrics surface must remain narrow and operational-only. |
| ARCH-ENTRY-001 | Transport adapters must stay thin | Architecture | Applicable | Health and metrics exposure must stay adapter-thin and avoid transport-owned runtime logic. |
| ARCH-COMP-001 | Composition must happen through registrars | Architecture | Applicable | Observability wiring should be assembled in `platform/composition/`, not ad hoc in routes. |
| ARCH-SHARED-001 | Shared and platform code must stay domain-neutral | Architecture | Applicable | Metrics, tracing, and telemetry belong in `platform/observability/` as runtime infrastructure. |
| OBS-CORE-001 | Failures must produce structured operational signals | Observability | Applicable | Telemetry must complement, not weaken, current structured logs and operational events. |
| OBS-CORR-001 | Correlation identifiers must survive subsystem boundaries | Observability | Applicable | Existing request/task/workflow correlation must survive telemetry rollout. |
| OBS-HEALTH-001 | Health endpoints must reflect operational truth | Observability | Applicable | Readiness metrics must reflect the same truth as health behavior. |
| OBS-DIAG-001 | Diagnostics surfaces must expose operator-relevant state | Observability | Applicable | Diagnostics should expose telemetry runtime state where useful without becoming a dashboard. |
| OBS-BG-001 | Background work must have visible terminal state | Observability | Applicable | Background task metrics must align with task snapshots, failures, and terminal states. |
| OBS-ALERT-001 | High-severity signals must be machine-usable for alerting | Observability | Applicable | Metrics and events should remain code-driven and machine-usable. |
| AGENT-RUN-001 | Runs and events must be persisted or inspectable | Agents | Non-Applicable | Agent-specific deeper instrumentation is not primary sprint scope, though later extension must remain possible. |
| AGENT-EXPOSE-001 | Operational exposure must flow through application modules | Agents | Ambiguous | A generic `/metrics` operational surface likely sits outside module-specific agent exposure, but agent runtime telemetry must still avoid direct transport ownership of agent internals. |

### Applicable Requirements

- **PRE-SCOPE-001:** This sprint is valid because the work is pure scaffold-stage foundation: observability runtime, metrics, tracing, middleware, and operational surfaces.
- **PRE-SCOPE-003:** The work must improve runtime visibility and operator confidence rather than invent product metrics, dashboards, or business alerts.
- **PRE-SCOPE-004:** The sprint may add an operational `/metrics` surface, but should not broaden product-facing API scope.
- **ARCH-ENTRY-001:** HTTP exposure must stay thin; route code should not own metrics registries or telemetry logic.
- **ARCH-COMP-001:** Telemetry configuration and runtime collaborators should be assembled in composition so instrumentation consumers depend on stable seams.
- **ARCH-SHARED-001:** Observability infrastructure must remain generic and live in platform code, not in modules or shared business abstractions.
- **OBS-CORE-001:** Adding metrics must not substitute for current failure visibility; structured logs and operational events remain mandatory.
- **OBS-CORR-001:** Existing `request_id` and `trace_id` propagation patterns must be reused rather than replaced inconsistently.
- **OBS-HEALTH-001:** Readiness metrics must track the same required-vs-optional dependency semantics as `HealthService`.
- **OBS-DIAG-001:** Diagnostics should expose telemetry enablement and runtime state in a canonical operator path when useful.
- **OBS-BG-001:** Background task instrumentation must align with explicit lifecycle transitions already maintained by `BackgroundTaskRunner`.
- **OBS-ALERT-001:** Stable codes, severity, component, and operation naming should stay machine-usable across logs, events, and metrics.

### Non-Applicable Requirements

- **AGENT-RUN-001:** The sprint does not need to redesign agent persistence or event inspection. It only needs to leave room for later agent telemetry instrumentation.

### Ambiguous Or Conflicting Requirements

- **AGENT-EXPOSE-001 and PRE-SCOPE-004:** A canonical `/metrics` endpoint is operational rather than product-facing, but it still adds a public transport surface. The safe interpretation is to keep it narrow, generic, and owned as infrastructure rather than as an agent or product capability.
- **OBS-DIAG-001 and PRE-SCOPE-004:** Diagnostics should expose telemetry runtime state, but the sprint should avoid turning diagnostics into a full monitoring dashboard.

### Open Questions

- Which exporter path should be first-class in scaffold stage: Prometheus metrics only, or Prometheus plus OpenTelemetry tracing in the same sprint?
- Should `/metrics` be enabled in all environments by default, or gated behind explicit settings in non-development environments?
- How much agent/provider/workflow instrumentation should be included now versus deferred to the next sprint after the base telemetry runtime exists?

## Feature Analysis

### Feature 1: Observability Runtime Foundation

**Description:** Add platform-owned metrics and telemetry runtime seams, configuration, and composition wiring that complement the existing logging and operational event infrastructure.

**Affected Areas**
- `backend/src/hello_sales_backend/platform/observability/`
- `backend/src/hello_sales_backend/platform/config/settings.py`
- `backend/src/hello_sales_backend/platform/composition/app_container.py`
- `backend/src/hello_sales_backend/app.py`
- `backend/.env.example`
- `backend/docs/configuration-and-environment.md`

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| PRE-SCOPE-001 | Keep the work generic and foundational | New observability runtime and settings | Tracker scope + code ownership in platform |
| ARCH-COMP-001 | Assemble runtime collaborators in composition | App container and startup wiring | Composition code review + integration tests |
| ARCH-SHARED-001 | Keep telemetry domain-neutral in platform | `platform/observability/*` only | File ownership and import direction review |
| OBS-CORE-001 | Preserve structured failure signaling | Logging/events remain in place next to metrics | Failure-path tests and emitted signals |
| OBS-CORR-001 | Preserve current correlation metadata | Trace/correlation propagation helpers and runtime config | Request/task integration tests |
| OBS-ALERT-001 | Keep signals machine-usable | Stable metric names and label discipline | Unit tests and review of metric schema |

**Current-System Analysis**
- The backend already has structured logging via `platform/observability/logging.py` and request correlation via `platform/observability/middleware.py`.
- `OperationalEvent`, `ObservabilityRuntime`, and in-memory alerts already provide an operator-visible event surface.
- `AppContainer` already owns observability runtime assembly and injects it into tasks and agent runtime.
- What must remain true is that telemetry augments the current runtime rather than becoming a parallel ad hoc path.

**Options Considered**
- **Option A:** Add metrics and tracing directly where needed with minimal abstraction.
- **Option B:** Add a platform-owned metrics/telemetry runtime with configuration and no-op behavior.
- **Option C:** Delay all telemetry wiring until a full external observability stack is chosen.

**Chosen Approach**
- Build a small platform-owned observability runtime seam with environment-driven enablement, safe defaults, and composition-root assembly.

**Decision Justification**
- Option B best fits the current codebase because the backend already centralizes observability concerns in `platform/observability/` and composes them through `AppContainer`.
- Option A would create scattered instrumentation ownership and make label/cardinality discipline harder to review.
- Option C would block a safe class of scaffold-stage operational work that the contracts explicitly allow.
- The main trade-off is introducing a new runtime abstraction now, but that cost is justified because it preserves replaceability and keeps future provider/agent instrumentation coherent.

**Execution Notes**
- Preserve existing logging, event emission, and correlation behavior unchanged unless explicitly extended.
- Keep disabled-mode behavior cheap and safe.
- If the exporter choice requires invasive startup behavior or network dependencies, revise reasoning before implementation.

**Expected Evidence**
- **Tests:** unit tests for settings, metric naming/labels, and no-op runtime behavior; integration tests for composition wiring.
- **Runtime Evidence:** logs and events still emit with existing structured fields; diagnostics can report telemetry enablement state.
- **Review Checks:** telemetry code remains in platform packages and is assembled through composition.

---

### Feature 2: Operational Metrics Surface And High-Signal Instrumentation

**Description:** Expose a narrow operational metrics surface and instrument HTTP, readiness, and background task boundaries with machine-usable counters, gauges, and durations.

**Affected Areas**
- `backend/src/hello_sales_backend/platform/observability/middleware.py`
- `backend/src/hello_sales_backend/platform/observability/health.py`
- `backend/src/hello_sales_backend/platform/tasks/runner.py`
- `backend/src/hello_sales_backend/entrypoints/http/routes/health.py`
- `backend/src/hello_sales_backend/app.py`
- `backend/src/hello_sales_backend/modules/system/use_cases/system_service.py`
- backend integration and smoke tests

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| PRE-SCOPE-004 | Keep the transport surface narrow and operational | `/metrics` endpoint scope and documentation | Route review + docs |
| ARCH-ENTRY-001 | Keep transport adapters thin | Endpoint exposure and request instrumentation | Route code review + integration tests |
| OBS-HEALTH-001 | Reflect operational truth in health-related telemetry | Readiness metrics and dependency state | Health tests and metrics assertions |
| OBS-DIAG-001 | Keep diagnostics canonical for telemetry state | Add summary state, not dashboard payloads | Diagnostics response verification |
| OBS-BG-001 | Keep task lifecycle visible through telemetry | Task state counters/gauges/histograms aligned with snapshots | Failure-path tests + task diagnostics |
| OBS-ALERT-001 | Keep alertable signals machine-usable | Metric labels based on stable code/component/operation/status | Unit review of metric schema |
| OBS-CORR-001 | Preserve request/task correlation through spans and metadata | HTTP/task instrumentation boundaries | Integration tests and structured runtime evidence |

**Current-System Analysis**
- HTTP middleware already captures request start/completion/failure and duration in structured logs.
- `HealthService` already models `live`, `ready`, and `degraded` truthfully with required dependency semantics.
- `BackgroundTaskRunner` already records snapshots, failures, and operational events with request and trace metadata.
- `SystemService` already exposes recent events and alerts through canonical diagnostics.
- What must remain true is that metrics align with the existing authoritative state rather than inventing a second truth source.

**Options Considered**
- **Option A:** Start with `/metrics` plus HTTP instrumentation only.
- **Option B:** Instrument HTTP, readiness, and background tasks in the first sprint.
- **Option C:** Instrument every subsystem including providers, workflows, and agents immediately.

**Chosen Approach**
- Implement `/metrics` and instrument HTTP, readiness, and background tasks first; leave provider, workflow, and agent-specific depth for a follow-up sprint.

**Decision Justification**
- Option B gives the best first-sprint coverage because these are already the highest-signal scaffold boundaries with clear existing truth models.
- Option A is safer but too shallow; it would create the endpoint without enough evidence that the telemetry model works across runtime boundaries.
- Option C is too broad for the first sprint and increases the risk of mixing foundational telemetry work with subsystem-specific instrumentation.
- The trade-off is that provider and agent telemetry remains incomplete after this sprint, but the foundation becomes testable and extensible.

**Execution Notes**
- Metric labels must avoid request ids, trace ids, raw messages, and other high-cardinality values.
- Readiness metrics should derive from the same dependency checks used by health responses.
- Background task metrics should use explicit lifecycle transitions already represented by task snapshots.
- If `/metrics` cannot be exposed cleanly without violating current architecture, revisit whether it belongs in app-level operational wiring instead of route-level code.

**Expected Evidence**
- **Tests:** integration tests for `/metrics`; unit/integration tests for HTTP/request/task metric emission; explicit failure-path verification for request failures and task failures.
- **Runtime Evidence:** metrics endpoint exposes counters/gauges/histograms; logs/events/diagnostics remain consistent with metric behavior.
- **Review Checks:** transport remains thin, diagnostics remains canonical, and no high-cardinality labels are introduced.

## Deviations

| Requirement ID | Deviation | Reason | Risk | Disposition | Follow-up |
| --- | --- | --- | --- | --- | --- |
| AGENT-RUN-001 | Agent-specific deep telemetry is deferred from this sprint | The first sprint is focused on foundation and highest-signal generic runtime boundaries | Agent observability remains partly dependent on existing events/logs instead of full metrics/tracing depth | Temporary | Add provider/workflow/agent instrumentation in the next observability sprint |

## Cross-Cutting Reasoning

### Major Decision Summary

- **Platform-owned observability foundation:** PRE-SCOPE-001, ARCH-COMP-001, and ARCH-SHARED-001 point toward a generic telemetry runtime assembled in composition rather than scattered instrumentation.
- **Instrument the existing truth boundaries first:** OBS-HEALTH-001, OBS-BG-001, and OBS-CORR-001 favor HTTP, readiness, and background tasks because those boundaries already have explicit lifecycle and correlation behavior.

### Trade-offs

- A runtime abstraction adds initial complexity, but it reduces future churn and keeps the architecture coherent.
- Deferring deeper provider/workflow/agent metrics limits first-sprint coverage, but preserves focus and reduces overreach during scaffold stage.

### Assumptions

- It is acceptable in scaffold stage to add a narrow operational `/metrics` surface.
- A no-op or environment-disabled telemetry mode is necessary to avoid making startup and local development fragile.
- Existing structured logs and operational events remain mandatory even after metrics and tracing are introduced.

### Dependencies

- **Existing observability runtime:** `platform/observability/runtime.py`, `logging.py`, `middleware.py`, and `events.py` provide the current authoritative seams.
- **Configuration model:** `platform/config/settings.py`, `platform/composition/startup.py`, `app.py`, and `backend/.env.example` will need coordinated updates.

### Evidence Review Checklist

- [ ] Review can trace every feature decision back to explicit requirement IDs
- [ ] Review can verify the planned tests and runtime evidence exist
- [ ] Review can identify any planned or unplanned deviations by requirement ID

## Phase Exit Criteria

- [ ] Tracker scope is fully covered
- [ ] Applicable requirements are mapped
- [ ] Ambiguous and non-applicable requirements are recorded where relevant
- [ ] Important decisions are explicitly justified
- [ ] Non-trivial alternatives are discussed
- [ ] Deviations, assumptions, risks, and unknowns are documented
- [ ] Expected evidence is defined

## Documentation Updates

- `backend/docs/errors-and-logging.md`: must reflect how metrics and tracing complement existing logs and operational events.
- `backend/docs/configuration-and-environment.md`: must document new observability settings and environment behavior.
- `backend/docs/runtime-overview.md`: should explain the observability runtime additions and operational surface changes.
- `backend/docs/diagnostics-and-events.md`: should describe how diagnostics and operational events relate to the new telemetry foundation.
