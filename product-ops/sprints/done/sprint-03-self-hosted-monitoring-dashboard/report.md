# Sprint Report: Self-Hosted Monitoring Dashboard

> Project: HelloSales
> Sprint ID: sprint-03-self-hosted-monitoring-dashboard
> Output: `ops/sprints/done/sprint-03-self-hosted-monitoring-dashboard/report.md`

## Overview

**Sprint:** Self-Hosted Monitoring Dashboard
**Status:** Completed
**Tracker:** `ops/sprints/done/sprint-03-self-hosted-monitoring-dashboard/tracker.md`
**Reasoning:** `ops/sprints/done/sprint-03-self-hosted-monitoring-dashboard/reasoning.md`

## TL;DR

- Sprint 3 delivered OTLP-capable tracing export, repo-owned self-hosted observability stack scaffolding, production-oriented Kubernetes deployment manifests, environment overlays, starter dashboards and alert rules, and updated canonical docs.
- Raw telemetry remains out of the main application database.
- Diagnostics now surface OTLP tracing configuration for operator inspection.
- Targeted unit, integration, smoke, Ruff, and Mypy checks passed.

## Change Summary

Sprint 3 extended the existing observability runtime so tracing can export to an OTLP HTTP endpoint suitable for a self-hosted OpenTelemetry Collector, added self-hosted stack scaffolding under `backend/ops/observability/`, added production-oriented Kubernetes deployment manifests and storage-hardening defaults under `backend/ops/observability/production/`, added `dev` / `staging` / `prod` overlays, added starter Grafana dashboard provisioning and Prometheus alert rules, and updated the canonical backend docs to explain the collector-oriented path and the role of future custom dashboard surfaces. The sprint did not implement a rich dashboard frontend; that remains follow-up work built on this backend and product-ops foundation.

## Planned vs Delivered

### OTLP Export And Self-Hosted Telemetry Wiring
- **Planned:** Add OTLP-capable tracing export and scaffold the self-hosted telemetry stack.
- **Delivered:** Added OTLP tracing exporter settings and runtime wiring, clean tracer shutdown, compose-based self-hosted stack scaffolding, local ops targets, a production-oriented Kubernetes manifest set with storage hardening, environment overlays, starter dashboards, and alert rules.
- **Status:** Done

### Internal Monitoring Surface Foundation
- **Planned:** Align docs and backend-facing monitoring surfaces with a future custom dashboard.
- **Delivered:** Updated diagnostics exposure and canonical docs; richer custom dashboard frontend remains deferred.
- **Status:** Partial

## Contract Adherence

### Sprint Reasoning Adherence

- **Status:** Planned Deviation
- **Notes:** Implementation matched the backend-first Sprint 3 reasoning. The only planned deviation is that the full custom dashboard frontend remains deferred in favor of exporter and stack groundwork.

### Governing Contract Conformance Matrix

| Requirement Area | Applicable Requirements | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| Architecture | PRE-SCOPE-004, ARCH-ENTRY-001, ARCH-COMP-001, ARCH-SHARED-001 | Conforming | `backend/src/hello_sales_backend/platform/observability/*`, `backend/ops/observability/*`, updated docs | Exporter, local stack, production manifests, overlays, and provisioning assets stayed in platform and ops-owned boundaries |
| Errors | ERR-CORE-001, ERR-STARTUP-001, ERR-HTTP-001, ERR-BG-001, ERR-DATA-001 | Conforming | tracer shutdown support, OTLP config validation, structured diagnostics exposure | No new silent failure path was introduced in the runtime slice delivered |
| Observability / Testing | OBS-CORE-001, OBS-CORR-001, OBS-HEALTH-001, OBS-DIAG-001, OBS-BG-001, OBS-ALERT-001, TEST-SEAM-001, TEST-INT-001, TEST-SMOKE-001, TEST-FAIL-001, TEST-DET-001 | Conforming | targeted pytest, Ruff, Mypy, diagnostics updates, stack scaffolding | OTLP config is inspectable and tested; broader provider smoke rerun deferred explicitly |

## Findings

### Blockers

- None.

### High

- None.

### Medium

- **[ops/sprints/done/sprint-03-self-hosted-monitoring-dashboard/reasoning.md]** The richer custom dashboard frontend was intentionally deferred. **Why it matters:** operator UX is still split between canonical diagnostics and future work. **Suggested fix:** build the dashboard UI over narrow backend-owned summary APIs in the next slice. **Evidence:** sprint tracker and reasoning deviation.

### Low / Nits

- **[backend/ops/observability/production/kubernetes/]** The production manifest set is a solid baseline but still cluster-generic. **Why it matters:** storage classes, ingress classes, TLS, and secret distribution must still be finalized per environment. **Suggested fix:** create environment overlays for each target cluster. **Evidence:** production README and manifest placeholders.

## Test & Verification Plan

- **CI:** `python3 -m ruff check backend/src backend/tests backend/ops backend/docs`, `python3 -m mypy backend/src`, targeted `pytest` for observability runtime and integration, broader suite as follow-up
- **Local:** observability unit/integration/smoke checks plus `make obs-up` stack bootstrap verification
- **Manual Checks:** verify collector-oriented tracing config, metrics exposure, self-hosted stack startup, dashboard provisioning, and production manifest review before cluster apply

### Testing Completed

- **Unit Tests:** `backend/tests/unit/test_observability_runtime.py`
- **Integration Tests:** `backend/tests/integration/test_observability.py`
- **Smoke Tests:** `backend/tests/smoke/test_http_metrics.py`
- **Failure Paths:** validated invalid OTLP endpoint handling and diagnostics behavior under OTLP exporter configuration
- **Coverage Gaps:** collector reachability, full stack bootstrap, dashboard rendering in a live Grafana instance, real cluster apply, and broader provider-backed smoke suite were not executed in this turn

## Security Notes

- **Threats Introduced Or Reduced:** OTLP exporter support reduces the need for console-only tracing and prepares the system for centralized telemetry transport; it introduces new external collector trust boundaries.
- **Secrets / Trust Boundaries:** OTLP headers may carry auth material and should be supplied through environment configuration, not committed values.
- **Supply-Chain / Dependency Notes:** Added `opentelemetry-exporter-otlp-proto-http` to support collector-oriented span export.
- **Required Follow-Ups:** cluster-specific overlay tuning, TLS, external auth, secret delivery, alert routing, and real cluster validation for the production observability stack.

## What Worked

- Existing observability seams were already clean enough to extend without transport-layer churn.
- The targeted test surface was strong enough to validate OTLP configuration and diagnostics quickly.

## Challenges

- OTLP exporter support required a clean shutdown path to avoid noisy background exporter errors in tests.
- Diagnostics views needed to be extended so configuration was actually inspectable rather than only internally present.

## Technical Debt

| Item | Type | Why | Impact | Follow-up |
| --- | --- | --- | --- | --- |
| Cluster-specific overlay tuning | Ops debt | The new `dev` / `staging` / `prod` overlays are environment-shaped but still use placeholder DNS, secrets, and default storage assumptions | Medium | Add real cluster-specific values and validate them against target clusters |

## Risks Carried Forward

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Self-hosted stack complexity exceeds current local scaffold | High | Keep compose stack clearly documented as development-oriented and use the new production manifests as a reviewed baseline instead of improvising cluster config |
| OTLP collector outages may still be under-tested | Medium | Add stack bootstrap and outage drills in the next slice |
| Production manifests may drift from target cluster realities | Medium | Tune the overlays with real storage, DNS, ingress, and secret delivery settings before rollout |
| Alert rules may not be actionable enough at first | Medium | Start with the provided rules, then tune thresholds after observing real traffic |

## Deferred Work

- Custom dashboard frontend: intentionally deferred until exporter and self-hosted pipeline groundwork are in place.
- Real cluster-specific overlay values, TLS, and secret-delivery wiring: deferred from this slice.
- Alert routing and notification delivery: deferred from this slice.

## Suggested Refactors / Future Work

- Expand dashboard-specific read models once the self-hosted telemetry pipeline is validated.
- Tune the overlays for each actual cluster and validate them against target environments.
- Add Alertmanager or another alert delivery path once the team chooses notification channels.

## Questions For The Author

- None at sprint start.

## Sign-Off

- Author: Codex
- Date: 2026-04-19
- Status: Final
