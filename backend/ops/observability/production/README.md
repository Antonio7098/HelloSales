# Production Observability Manifests

This directory contains production-oriented Kubernetes manifests for the HelloSales self-hosted observability stack.

## Scope

The manifests provide a hardened starting point for:
- OpenTelemetry Collector
- Prometheus
- Loki
- Tempo
- Grafana
- MinIO

They are designed for production-like deployment shape, not for local convenience.

## Layout

- `kubernetes/kustomization.yaml`: top-level manifest entrypoint
- `kubernetes/namespace.yaml`: dedicated namespace
- `kubernetes/secrets.template.yaml`: placeholder secret manifest to copy and fill out outside version control
- `kubernetes/minio-lifecycle-configmap.yaml`: bucket lifecycle and retention templates
- `kubernetes/minio-bootstrap-job.yaml`: bucket creation, versioning, and lifecycle bootstrap
- individual workload, service, pvc, and network-policy manifests for each component

## Hardening Decisions

- dedicated namespace: `hello-sales-observability`
- persistent volumes for all stateful components
- non-root containers where supported
- dropped Linux capabilities and `RuntimeDefault` seccomp profile
- explicit resource requests and limits
- default-deny network policy with explicit allow rules
- Grafana admin credentials and MinIO root credentials supplied through Secrets
- Loki and Tempo configured against S3-compatible object storage instead of ephemeral local files

## Storage Model

- MinIO is included here as the in-cluster S3-compatible object storage backend
- Loki stores chunks and index data in MinIO bucket `loki`
- Tempo stores traces in MinIO bucket `tempo`
- a separate bucket `observability-backups` is created for future snapshot or export workflows

## Retention Model

- Prometheus hot retention: `30d`
- Loki hot retention: `30d`
- Tempo hot retention: `14d`
- MinIO lifecycle policies expire the corresponding bucket objects on matching timelines

These values are defaults, not universal policy. Adjust them to match cost, compliance, and incident-response needs.

## Before Apply

1. Copy `secrets.template.yaml` into your private deployment repo or secret-management workflow.
2. Replace placeholder values.
3. Confirm storage classes and ingress class names for the target cluster.
4. Review resource sizing against the cluster.
5. Confirm TLS and external auth strategy for Grafana and any exposed operator surfaces.

`secrets.template.yaml` is intentionally not included in `kustomization.yaml`. Create the real Secret through your secret-management workflow before applying the rest of the manifests.

## Apply

From `backend/ops/observability/production/kubernetes/`:

```bash
kubectl apply -k .
```

## Important Boundary

These manifests harden the observability stack. They do not make the application database a telemetry store, and they do not replace canonical backend diagnostics under `/api/system/diagnostics`.
