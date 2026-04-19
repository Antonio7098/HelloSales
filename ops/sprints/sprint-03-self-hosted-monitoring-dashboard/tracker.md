# Sprint Tracker: Self-Hosted Monitoring Dashboard

> Project: HelloSales
> Sprint ID: sprint-03-self-hosted-monitoring-dashboard
> Created: 2026-04-19

## Sprint Overview

- **Sprint Name:** Self-Hosted Monitoring Dashboard
- **Sprint Focus:** Extend the backend telemetry foundation into a self-hosted observability pipeline and lay the backend groundwork for a custom internal monitoring dashboard.
- **Depends On:** `ops/sprints/sprint-01-observability-foundation/tracker.md`
- **Status:** In Progress

## Sprint Goals

- **Primary Goal:** Add OTLP-capable telemetry export and self-hosted observability stack scaffolding without using the main application database as the raw telemetry store.
- **Secondary Goals:**
  - Keep canonical diagnostics and operator surfaces aligned with the self-hosted stack.
  - Add repo-owned self-hosted observability configuration for collector, Grafana, Loki, Tempo, Prometheus, and object storage.
  - Prepare the backend for a custom internal dashboard by documenting and preserving narrow operational read surfaces.

## Execution Checklist

- [x] **Task 1: Formalize Sprint 3 artifacts and branch setup**
  > *Description: Move the monitoring work into a proper sprint artifact set, align it with the execution protocol, and execute on the correct branch.*
  - [x] **Sub-task 1.1:** Move the sprint reasoning and tracker into `ops/sprints/sprint-03-self-hosted-monitoring-dashboard/`.
  - [x] **Sub-task 1.2:** Start work from `sprint/sprint-03-self-hosted-monitoring-dashboard`.

- [x] **Task 2: Add OTLP-capable tracing export**
  > *Description: Extend the current tracing runtime so the backend can export spans to a self-hosted OpenTelemetry Collector instead of only console output.*
  - [x] **Sub-task 2.1:** Extend backend config and observability runtime to support OTLP tracing export settings and validation.
  - [x] **Sub-task 2.2:** Add tests proving OTLP tracing configuration and diagnostics behavior while preserving current trace-id reuse semantics.

- [x] **Task 3: Scaffold the self-hosted observability stack**
  > *Description: Add repo-owned configuration for the first self-hosted observability deployment slice.*
  - [x] **Sub-task 3.1:** Add OpenTelemetry Collector, Prometheus, Loki, Tempo, Grafana, and MinIO configuration files.
  - [x] **Sub-task 3.2:** Add a compose-based local stack or equivalent bootstrap for self-hosted observability development.
  - [x] **Sub-task 3.3:** Document intended retention and hosting boundaries for the stack.
  - [x] **Sub-task 3.4:** Add production-oriented Kubernetes manifests and storage hardening for the self-hosted stack.
  - [x] **Sub-task 3.5:** Add environment overlays for `dev`, `staging`, and `prod`.
  - [x] **Sub-task 3.6:** Add starter Grafana dashboard provisioning and Prometheus alert rules.

- [x] **Task 4: Align operator documentation and dashboard foundation**
  > *Description: Update canonical docs so the self-hosted stack and internal monitoring surface are described accurately and remain aligned with the backend runtime.*
  - [x] **Sub-task 4.1:** Update backend observability docs for OTLP exporter and collector-oriented deployment.
  - [x] **Sub-task 4.2:** Document how canonical diagnostics and future dashboard surfaces relate to Grafana and raw telemetry backends.
  - [x] **Sub-task 4.3:** Add a detailed backend hosting guide for operators new to monitoring infrastructure.

- [x] **Task 5: Verify and record execution evidence**
  > *Description: Produce test and execution evidence required by the sprint reasoning and execution protocol.*
  - [x] **Sub-task 5.1:** Run relevant unit, integration, and smoke checks for the observability changes.
  - [x] **Sub-task 5.2:** Update tracker evidence and status based on what passed or was explicitly deferred.

## Testing And Documentation Checklist

- [x] **Unit Tests:** deterministic coverage for OTLP settings validation and tracing runtime behavior
- [x] **Integration Tests:** observability diagnostics and exporter configuration coverage for the sprint scope
- [ ] **Smoke Tests With Real Provider:** baseline backend smoke suite still passes or any deferral is recorded explicitly
- [x] **Documentation Updates:** update canonical documentation in `docs/`

## Risks And Blockers

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| OTLP exporter configuration introduces startup or dependency fragility | Medium | Keep exporter environment-driven and preserve `none` and `console` safe paths | Open |
| Self-hosted stack config drifts from actual backend behavior | High | Keep stack config in repo and update backend docs in the same sprint | Open |
| Sprint scope expands into a full dashboard frontend before the backend pipeline is ready | Medium | Keep this sprint backend- and infra-first, and record the frontend as explicit follow-up work | Mitigated |
| Observability backends are treated as required for core API readiness too early | Medium | Preserve optional/degraded semantics for the main API unless explicitly configured otherwise | Open |

## Success Criteria

- [x] **Success Criteria 1:** The backend supports OTLP-capable tracing export suitable for a self-hosted collector.
- [x] **Success Criteria 2:** Repo-owned self-hosted observability stack configuration exists for local or development bootstrap.
- [x] **Success Criteria 3:** Canonical backend docs explain the self-hosted telemetry path and operator-surface boundaries.

## Review And Sign-Off

- Sprint Status: Completed
- Completion Date: 2026-04-19

## Execution Evidence

- `python3 -m pytest backend/tests/unit/test_observability_runtime.py backend/tests/integration/test_observability.py backend/tests/smoke/test_http_metrics.py -q` passed with `14 passed`
- `python3 -m ruff check backend/src backend/tests backend/ops backend/docs` passed
- `python3 -m mypy backend/src` passed
- Added OTLP tracing exporter settings, runtime support, diagnostics exposure, and clean tracer shutdown on app teardown
- Added repo-owned self-hosted observability stack scaffolding under `backend/ops/observability/`
- Added production-oriented Kubernetes manifests and storage hardening under `backend/ops/observability/production/kubernetes/`
- Added environment overlays for `dev`, `staging`, and `prod` under `backend/ops/observability/production/kubernetes/overlays/`
- Added starter Grafana dashboard provisioning and Prometheus alert rules for both local and production paths
- Updated backend docs for OTLP export, collector-oriented deployment, and the boundary between canonical diagnostics, Grafana, and a future custom internal dashboard
- Added `backend/docs/observability-hosting-guide.md` with a step-by-step hosting guide for first-time operators
- Validated the production manifest tree parses as YAML
- Validated the starter Grafana dashboard JSON parses cleanly
- Broader provider-backed smoke suites were not rerun in this turn because Sprint 3 changed observability plumbing rather than provider execution logic
