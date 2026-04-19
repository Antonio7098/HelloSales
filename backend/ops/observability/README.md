# Self-Hosted Observability Stack

This directory contains the first self-hosted observability stack scaffold for HelloSales.

## Purpose

The stack is intended to support:
- Prometheus metrics scraping from the backend `/metrics` surface
- OTLP trace export from the backend into an OpenTelemetry Collector
- Loki for log storage
- Tempo for trace storage
- Grafana for operator dashboards and drilldowns
- MinIO as S3-compatible object storage for longer-term retention and backend storage evolution

## Layout

- `docker-compose.observability.yml`: local bootstrap for the self-hosted stack
- `otel-collector/config.yaml`: collector receivers, processors, and exporters
- `prometheus/prometheus.yml`: Prometheus scrape config
- `loki/config.yaml`: Loki local config with explicit retention
- `tempo/config.yaml`: Tempo local config with explicit retention
- `grafana/provisioning/`: Grafana datasource provisioning
- `production/`: production-oriented Kubernetes manifests and storage hardening

## Intended Local Flow

1. Start the stack with `make obs-up` from `backend/`
2. Run the backend with:
   - `HELLO_SALES_OBSERVABILITY_METRICS_ENABLED=true`
   - `HELLO_SALES_OBSERVABILITY_METRICS_ENDPOINT_ENABLED=true`
   - `HELLO_SALES_OBSERVABILITY_TRACING_ENABLED=true`
   - `HELLO_SALES_OBSERVABILITY_TRACING_EXPORTER=otlp`
   - `HELLO_SALES_OBSERVABILITY_TRACING_OTLP_ENDPOINT=http://localhost:4318/v1/traces`
3. Visit Grafana on `http://localhost:3001`

## Retention Defaults In This Scaffold

- Prometheus hot metrics retention: `30d`
- Loki hot log retention: `30d`
- Tempo hot trace retention: `14d`

These are starter values for local and development use, not final production sizing.

## Production Manifests

Production-oriented manifests now live under `production/kubernetes/`.

That manifest set adds:
- dedicated namespace and service account
- RBAC for Prometheus Kubernetes service discovery
- non-root workload security contexts
- PVC-backed stateful storage
- MinIO bucket bootstrap and lifecycle policies
- network policies for internal traffic, app-to-collector traffic, and ingress-to-Grafana traffic
- ingress-ready Grafana exposure

Use the production README before applying those manifests. The production set is a deployment baseline, not a claim that the local compose stack is production-safe.

## Important Boundaries

- Raw telemetry does not belong in the main application database.
- Canonical app diagnostics still belong to the backend under `/api/system/diagnostics`.
- Grafana is the raw telemetry workbench.
- A future custom internal dashboard should be built over app-owned summary APIs and diagnostics, not direct access to application internals.
