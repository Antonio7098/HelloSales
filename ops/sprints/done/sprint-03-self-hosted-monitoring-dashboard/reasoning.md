# Sprint Reasoning: Self-Hosted Monitoring Dashboard

> Project: HelloSales
> Sprint ID: sprint-03-self-hosted-monitoring-dashboard
> Output: `ops/sprints/sprint-03-self-hosted-monitoring-dashboard/reasoning.md`

## Overview

**Sprint:** Self-Hosted Monitoring Dashboard
**Purpose:** Extend the existing backend telemetry foundation into a self-hosted observability pipeline and lay the backend and infrastructure groundwork for a custom internal monitoring dashboard.
**Tracker:** `ops/sprints/sprint-03-self-hosted-monitoring-dashboard/tracker.md`
**Depends On:** `ops/sprints/done/sprint-01-observability-foundation/tracker.md`

## Requirement Map

### Contract Coverage Reviewed For This Sprint

| Contract File | Area | Applicability | Why It Matters |
| --- | --- | --- | --- |
| `ops/operational-contract/architecture.md` | Layering and dependency direction | Applicable | Exporters, collectors, dashboard read models, and operational routes must stay within explicit platform and module boundaries. |
| `ops/operational-contract/errors.md` | Failure visibility and canonical shape | Applicable | Telemetry exporter failures, collector outages, and dashboard query errors must be visible and preserve structured signals. |
| `ops/operational-contract/observability.md` | Logging, correlation, health, diagnostics, and alertability | Applicable | The sprint directly extends observability surfaces, telemetry transport, retention posture, and operator-facing inspection. |
| `ops/operational-contract/testing.md` | Verification expectations | Applicable | Exporter wiring, self-hosted stack bootstrap, and new dashboard-facing APIs require integration and failure-path evidence. |
| `ops/operational-contract/pre-brief-scope.md` | Pre-brief limits and safe scaffolding | Applicable | Self-hosted monitoring and internal dashboards are allowed scaffold-stage work, but product analytics and broad public APIs remain out of scope. |

### Requirement Index Used In This Sprint

| Requirement ID | Title | Area | Applicability | Why It Matters For This Sprint |
| --- | --- | --- | --- | --- |
| PRE-SCOPE-001 | Foundation work may proceed before the brief | Pre-Brief Scope | Applicable | Self-hosted telemetry infrastructure and an internal monitoring surface are valid scaffold-stage work. |
| PRE-SCOPE-003 | Operational scaffolding should be favored over product assumptions | Pre-Brief Scope | Applicable | The sprint focuses on operator visibility, telemetry transport, and infrastructure scaffolding rather than speculative product analytics. |
| PRE-SCOPE-004 | Public APIs must remain intentionally narrow before the brief | Pre-Brief Scope | Applicable | Dashboard-facing APIs must remain internal operational surfaces. |
| ARCH-CORE-002 | Dependency direction must point inward | Architecture | Applicable | Dashboard readers and telemetry export code must depend on app-owned seams rather than UI or transport code reaching into internals. |
| ARCH-ENTRY-001 | Transport adapters must stay thin | Architecture | Applicable | Dashboard summary endpoints must remain adapters over canonical services and read models. |
| ARCH-COMP-001 | Composition must happen through registrars | Architecture | Applicable | Telemetry exporter setup and dashboard service wiring should stay in composition and platform-owned runtime code. |
| ARCH-SHARED-001 | Shared and platform code must stay domain-neutral | Architecture | Applicable | Telemetry exporters, collector config, and retention scaffolding belong in `platform/` and ops config rather than bounded-context modules. |
| ERR-CORE-001 | No failure may disappear | Errors | Applicable | Exporter, collector, and storage failures must remain explicit and inspectable. |
| ERR-STARTUP-001 | Known-fatal startup failures must fail before traffic | Errors | Applicable | Required dashboard-serving dependencies should fail clearly at startup if they are mandatory in a given deployment mode. |
| ERR-HTTP-001 | Transport adapters must preserve the operational signal | Errors | Applicable | Internal dashboard APIs should preserve stable error codes and correlation metadata. |
| ERR-BG-001 | Background work must end in explicit inspectable failure state | Errors | Applicable | Retention, archival, and maintenance tasks must have owned terminal state. |
| ERR-DATA-001 | Persistence and data failures must be loud and distinct | Errors | Applicable | Telemetry storage backends are separate persistence systems and their failures must remain explicit. |
| OBS-CORE-001 | Failures must produce structured operational signals | Observability | Applicable | The monitoring stack itself must be observable through logs, events, metrics, and diagnostics. |
| OBS-CORR-001 | Correlation identifiers must survive subsystem boundaries | Observability | Applicable | Request and task correlation must survive export into logs, metrics, and traces backends. |
| OBS-HEALTH-001 | Health endpoints must reflect operational truth | Observability | Applicable | Core app readiness and dashboard stack health must model required versus optional dependencies truthfully. |
| OBS-DIAG-001 | Diagnostics surfaces must expose operator-relevant state | Observability | Applicable | Dashboard summary services should extend canonical diagnostics rather than create hidden debug paths. |
| OBS-BG-001 | Background work must have visible terminal state | Observability | Applicable | Telemetry maintenance jobs need visible lifecycle state. |
| OBS-ALERT-001 | High-severity signals must be machine-usable for alerting | Observability | Applicable | Collector failure, storage pressure, and retention failures should be alertable using stable metrics and codes. |
| TEST-SEAM-001 | Collaborators must be replaceable through public seams | Testing | Applicable | Exporters, telemetry readers, and dashboard summary services should be replaceable in tests. |
| TEST-INT-001 | Wiring and persistence changes must have integration coverage | Testing | Applicable | Exporter wiring and dashboard API additions require integration tests. |
| TEST-SMOKE-001 | Critical runtime paths must have smoke coverage | Testing | Applicable | Metrics exposure and self-hosted stack bootstrap need smoke-level verification. |
| TEST-FAIL-001 | Failure paths must be tested explicitly | Testing | Applicable | Exporter disablement, invalid exporter config, and dashboard read failures need explicit tests. |
| TEST-DET-001 | Tests must remain deterministic and non-brittle | Testing | Applicable | Telemetry tests should target stable signals and configuration state rather than timing-sensitive exact output. |

### Applicable Requirements

- **PRE-SCOPE-001 / PRE-SCOPE-003:** This sprint is safe pre-brief infrastructure work because it strengthens runtime visibility, deployment scaffolding, and operator workflows without forcing product-specific behavior.
- **PRE-SCOPE-004:** Any added backend endpoints must remain internal and operational rather than broadening the public API.
- **ARCH-CORE-002 / ARCH-ENTRY-001 / ARCH-COMP-001 / ARCH-SHARED-001:** Observability transport, self-hosted configs, and dashboard backend surfaces must stay within platform-owned seams and thin adapters.
- **ERR-CORE-001 / ERR-STARTUP-001 / ERR-BG-001 / ERR-DATA-001:** Telemetry pipeline failures, maintenance job failures, and storage failures must be explicit and inspectable.
- **OBS-CORE-001 / OBS-CORR-001 / OBS-HEALTH-001 / OBS-DIAG-001 / OBS-BG-001 / OBS-ALERT-001:** The stack must preserve structured, correlated, machine-usable telemetry and expose canonical operator-relevant state.
- **TEST-SEAM-001 / TEST-INT-001 / TEST-SMOKE-001 / TEST-FAIL-001 / TEST-DET-001:** Exporter wiring, stack scaffolding, and dashboard read services require deterministic unit, integration, smoke, and explicit failure-path evidence.

### Non-Applicable Requirements

- None identified. The sprint directly affects architecture, errors, observability, testing, and pre-brief scope.

### Ambiguous Or Conflicting Requirements

- **PRE-SCOPE-004 and custom dashboard breadth:** The dashboard can be rich as an internal operational surface, but it must not become speculative product analytics. The safe interpretation is to keep it internal, authenticated, and operationally narrow.
- **OBS-HEALTH-001 and telemetry optionality:** The main application should not fail readiness purely because an optional log or trace backend is degraded. The safe interpretation is to make telemetry dependencies required for observability services where configured, but only degradations for the main API unless explicitly made mandatory.

### Resolved Decisions

- **Storage separation:** Raw telemetry will not be stored in the main application database.
- **Exporter path:** Extend tracing from `console`/`none` to include OTLP export suitable for an OpenTelemetry Collector.
- **Self-hosted stack:** Use a self-hosted stack centered on OpenTelemetry Collector, Prometheus, Loki, Tempo, Grafana, and S3-compatible object storage.
- **Dashboard stance:** In this sprint, prioritize backend and infrastructure groundwork plus internal summary APIs; a richer frontend can extend this foundation later.
- **Retention stance:** Document and scaffold tiered retention with short hot retention and longer archive retention rather than keeping all telemetry hot.

## Feature Analysis

### Feature 1: OTLP Export And Self-Hosted Telemetry Wiring

**Description:** Extend the backend observability runtime to support OTLP trace export and add self-hosted observability stack scaffolding.

**Affected Areas**
- `backend/src/hello_sales_backend/platform/observability/`
- `backend/src/hello_sales_backend/platform/config/settings.py`
- `backend/pyproject.toml`
- backend observability deployment/config files

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-COMP-001 | Exporter setup must be composed centrally | tracing runtime build path | Integration tests and code review |
| ARCH-SHARED-001 | Exporter logic remains platform-owned | `platform/observability/*` only | File ownership review |
| ERR-DATA-001 | Telemetry backend failures remain explicit | exporter setup and pipeline docs | Failure-path tests and structured signals |
| OBS-CORR-001 | Correlation survives export boundaries | trace and request-id propagation | Unit/integration tests |
| OBS-ALERT-001 | Self-hosted backend should support alertable machine-usable signals | exporter config and stack scaffolding | Config review and docs |
| TEST-INT-001 | Wiring changes need integration coverage | settings/runtime and diagnostics | Integration tests |

**Current-System Analysis**
- The backend already emits structured logs, Prometheus metrics, and OpenTelemetry spans.
- Tracing currently supports only `console` or disabled mode.
- There is no self-hosted collector or backend stack scaffolding yet.
- What must remain true is that the observability runtime remains the canonical producer and the self-hosted stack becomes the durable sink.

**Options Considered**
- **Option A:** Keep console tracing and defer OTLP until later.
- **Option B:** Add OTLP export now and scaffold the self-hosted stack config in the same sprint.
- **Option C:** Jump directly to full log/trace/metric ingestion code plus retention jobs and custom dashboard frontend.

**Chosen Approach**
- Adopt Option B. Add OTLP export support now and scaffold the self-hosted observability stack so Sprint 3 has real backend and ops progress without over-claiming a full dashboard delivery in one slice.

**Decision Justification**
- Option B gives immediate durable telemetry progress and aligns with the user’s desired self-hosted direction.
- Option A would leave the sprint with only planning artifacts again.
- Option C is too broad for one bounded execution slice and would risk violating the execution protocol by leaving tracker, tests, and code misaligned.

**Execution Notes**
- Keep existing trace correlation semantics unchanged.
- Preserve `none` and `console` tracing exporters.
- Use OTLP HTTP exporter configuration that can target a collector endpoint.
- Add self-hosted stack config in repo-owned ops files, not as undocumented tribal knowledge.

**Expected Evidence**
- **Tests:** unit coverage for settings validation and OTLP runtime behavior; integration coverage for diagnostics state.
- **Runtime Evidence:** tracing diagnostics surface reflects OTLP exporter configuration and the app still emits spans.
- **Review Checks:** no product modules own exporter code; self-hosted config exists in the repo.

---

### Feature 2: Internal Monitoring Surface Foundation

**Description:** Prepare the backend and sprint artifacts for a custom internal monitoring dashboard without broadening the public product API.

**Affected Areas**
- `ops/sprints/sprint-03-self-hosted-monitoring-dashboard/`
- backend docs
- dashboard-oriented internal summary APIs where needed

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| PRE-SCOPE-004 | Keep surfaces internal and operational | dashboard-oriented routes and docs | Route and docs review |
| ARCH-ENTRY-001 | Keep adapters thin | any dashboard summary endpoint | Code review and integration tests |
| OBS-DIAG-001 | Prefer canonical diagnostics and stable read models | system diagnostics and summary views | Docs and integration evidence |
| ERR-HTTP-001 | Preserve structured failure signals on internal APIs | internal route behavior | Failure-path tests |

**Current-System Analysis**
- The backend already has `/api/system/diagnostics` as the canonical in-process operator surface.
- The richer dashboard does not exist yet.
- What must remain true is that new operator surfaces build on canonical diagnostics and stable read models rather than ad hoc route-local logic.

**Options Considered**
- **Option A:** Defer all dashboard-facing backend work until after infra is live.
- **Option B:** Add the first internal operational summary surfaces in this sprint while keeping them narrow.
- **Option C:** Build a full dashboard frontend immediately.

**Chosen Approach**
- Adopt Option B in a narrow form. Establish sprint artifacts, docs, and the backend-facing foundation now; richer frontend work remains follow-up.

**Decision Justification**
- Option B keeps the sprint execution real and aligned with the user’s request for a custom dashboard path.
- Option C is too large for the current execution slice and would undercut verification quality.

**Execution Notes**
- Keep this sprint focused on backend and infrastructure scaffolding.
- Any new routes should remain internal and narrow.

**Expected Evidence**
- **Tests:** integration coverage for any new dashboard-oriented backend surface added this sprint.
- **Runtime Evidence:** canonical diagnostics remain intact and documented as the source for the internal dashboard.
- **Review Checks:** no speculative product analytics surfaces are introduced.

## Deviations

| Requirement ID | Deviation | Reason | Risk | Disposition | Follow-up |
| --- | --- | --- | --- | --- | --- |
| PRE-SCOPE-004 | Full custom dashboard frontend is deferred from the first Sprint 3 execution slice | The sprint begins with backend/exporter/infra groundwork to preserve implementation quality and verification coverage | UI delivery is incomplete in this slice | Temporary | Extend Sprint 3 or Sprint 4 with the frontend once the telemetry pipeline is live |

## Cross-Cutting Reasoning

### Major Decision Summary

- **Backend-first observability extension:** PRE-SCOPE-001, ARCH-COMP-001, and OBS-CORR-001 point toward adding OTLP export and self-hosted stack scaffolding before building a richer custom UI.
- **Storage separation:** OBS-CORE-001, ERR-DATA-001, and PRE-SCOPE-003 all support keeping raw telemetry out of the main application database.

### Trade-offs

- Adding OTLP export and self-hosted stack config increases infrastructure complexity, but it is the necessary cost of full self-hosting.
- Deferring the fuller custom dashboard frontend keeps the execution slice reviewable and testable, but means the operator UI remains partial for now.

### Assumptions

- The app should continue to work when tracing is disabled or routed to `none`.
- OTLP export should be environment-driven and safe to leave disabled in local development.
- Self-hosted stack config in-repo is valuable evidence even before full production deployment.

### Dependencies

- `ops/sprints/done/sprint-01-observability-foundation/`: provides the canonical observability runtime this sprint extends.
- `backend/docs/*`: must be updated to explain OTLP export and the self-hosted stack.

### Evidence Review Checklist

- [x] Review can trace every feature decision back to explicit requirement IDs
- [x] Review can verify the planned tests and runtime evidence exist
- [x] Review can identify planned deviations and follow-up scope

## Phase Exit Criteria

- [x] Tracker scope is fully covered
- [x] Applicable requirements are mapped
- [x] Ambiguous and non-applicable requirements are recorded where relevant
- [x] Important decisions are explicitly justified
- [x] Non-trivial alternatives are discussed
- [x] Deviations, assumptions, risks, and unknowns are documented
- [x] Expected evidence is defined

## Documentation Updates

- `backend/docs/configuration-and-environment.md`: add OTLP exporter and self-hosted stack configuration.
- `backend/docs/runtime-overview.md`: explain how the observability runtime now supports collector-oriented export.
- `backend/docs/diagnostics-and-events.md`: describe how canonical diagnostics relate to self-hosted telemetry backends and the planned custom dashboard.
