# Observability Hosting Guide

## Purpose

This guide explains how to host the HelloSales observability stack that now exists in the repo.

It is written for someone who has not hosted monitoring infrastructure before.

The goal is not just to list commands. The goal is to explain:
- what each component does
- why it exists
- what order to deploy things in
- what to configure before going live
- what to validate after deployment
- what can go wrong

## What You Are Hosting

The stack created in this repo has six core parts:

1. **HelloSales backend**
   - emits Prometheus metrics from `/metrics`
   - emits OpenTelemetry traces over OTLP HTTP
   - emits structured JSON logs

2. **OpenTelemetry Collector**
   - receives traces and logs from the app
   - forwards them to the storage backends
   - acts as the first boundary between the app and observability storage

3. **Prometheus**
   - scrapes `/metrics`
   - stores time-series metrics
   - evaluates alert rules

4. **Loki**
   - stores logs

5. **Tempo**
   - stores traces

6. **Grafana**
   - gives you dashboards and drill-down views into metrics, logs, and traces

7. **MinIO**
   - provides S3-compatible object storage
   - stores Loki and Tempo data
   - gives you explicit lifecycle and retention control

## What Each Component Is For

If you are new to monitoring infrastructure, the easiest mistake is to treat everything as “just logging.”
It is not.

- **Metrics** answer: how much, how often, how slow, how many failures.
- **Logs** answer: what exactly happened in a specific request, task, worker, or failure.
- **Traces** answer: how one request or task moved across boundaries over time.
- **Dashboards** answer: what needs attention right now.
- **Alerts** answer: what has crossed a threshold and should wake a human up or create an incident.
- **Object storage** answers: where durable observability data lives without turning your main database into a telemetry store.

## What This Repo Gives You Now

Under `backend/ops/observability/` you now have:

- a local compose stack for development
- starter Grafana datasources and dashboards
- starter Prometheus alert rules
- a production-oriented Kubernetes manifest set
- environment overlays for `dev`, `staging`, and `prod`

Under the production tree:

- `production/kubernetes/`
  - base manifests
- `production/kubernetes/overlays/dev/`
- `production/kubernetes/overlays/staging/`
- `production/kubernetes/overlays/prod/`

## Which Path To Use

Use the local compose stack if:
- you are learning the stack
- you want to see dashboards quickly
- you are validating the app emits the expected signals

Use the Kubernetes production manifests if:
- you want a real hosted deployment
- you need persistent storage, network controls, and ingress-ready services
- you want the deployment shape you will eventually operate in production

## High-Level Hosting Plan

Follow this order:

1. Choose where the observability stack will run.
2. Provision storage capacity.
3. Provision DNS and TLS for Grafana.
4. Create and store secrets.
5. Deploy MinIO first.
6. Run the MinIO bootstrap job to create buckets and lifecycle policies.
7. Deploy Loki and Tempo.
8. Deploy the OpenTelemetry Collector.
9. Deploy Prometheus.
10. Deploy Grafana.
11. Point the HelloSales backend at the collector.
12. Verify metrics, logs, and traces.
13. Verify dashboards and alerts.
14. Run a failure drill.

That order matters. If you skip around, you will spend time debugging things that are simply not ready yet.

## Step 1: Choose Where To Host It

If you have never hosted monitoring infrastructure before, the best self-hosted starting point is:

- one Kubernetes cluster you already trust
- one dedicated namespace for observability
- persistent volumes available through your cluster storage class
- one ingress controller already working
- DNS you can point at Grafana

Do not put this on the same VM as your application database if you can avoid it.

Why:
- telemetry is noisy and bursty
- disk pressure from logs and traces can hurt the database
- memory pressure from Prometheus queries can hurt the database
- operational isolation matters more than convenience here

## Step 2: Decide The Environment First

This repo already gives you overlays for:
- `dev`
- `staging`
- `prod`

Use:

```bash
backend/ops/observability/production/kubernetes/overlays/dev
backend/ops/observability/production/kubernetes/overlays/staging
backend/ops/observability/production/kubernetes/overlays/prod
```

Start with `staging` unless you are only testing locally.

## Step 3: Prepare Secrets

Do not apply placeholder secret files as-is.

Each overlay contains a `*-secrets.template.yaml` file. Treat it as a shape reference only.

You need to create real values for:
- Grafana admin username and password
- MinIO root username and password
- MinIO access key and secret key

Best practice:
- store them in your secret-management system
- render the real Kubernetes Secret outside this repo
- never commit real values back into git

## Step 4: Review Cluster-Specific Settings

Before applying anything, review:

- `storageClassName`
  - the current manifests request PVCs but do not pin a storage class
  - if your cluster has multiple storage classes, add the correct one in your overlay

- ingress class
  - the base manifests assume `nginx`
  - if you use Traefik, AWS ALB, GKE ingress, or something else, patch it

- DNS names
  - the overlays use example hostnames
  - replace them with real names

- TLS
  - the ingress is HTTPS-oriented but not wired to your cert manager automatically
  - patch TLS blocks and annotations for your environment

- namespace selectors in network policies
  - the policies assume namespace labels like `kubernetes.io/metadata.name`
  - confirm those labels exist in your cluster

## Step 5: Understand The Storage Hardening

The most important production hardening added here is storage separation and lifecycle control.

### MinIO

MinIO is acting as object storage.

Buckets:
- `loki`
- `tempo`
- `observability-backups`

The bootstrap job does this:
- creates buckets if missing
- enables versioning
- disables anonymous access
- applies lifecycle policies

### Retention Defaults

Current defaults:
- Prometheus: `30d`
- Loki: `30d`
- Tempo: `14d`
- backups bucket lifecycle: `180d`

These are reasonable starting points, not sacred values.

If you are new to this, keep them short first.
Short retention is safer than discovering too late that your cluster disk or object store costs are exploding.

## Step 6: Deploy In The Right Order

From the chosen overlay directory, render manifests first:

```bash
kubectl kustomize .
```

Review that output before apply.

Then apply:

```bash
kubectl apply -k .
```

Recommended deployment order to validate:

1. `Namespace`, RBAC, ConfigMaps, and Secrets
2. `MinIO`
3. `MinIO bootstrap Job`
4. `Loki`
5. `Tempo`
6. `OpenTelemetry Collector`
7. `Prometheus`
8. `Grafana`

Why this order:
- Loki and Tempo depend on object storage
- the collector depends on Loki and Tempo being available
- Grafana is most useful only once the data sources are alive

## Step 7: Point The Backend At The Collector

Set these environment variables on the HelloSales backend:

```env
HELLO_SALES_OBSERVABILITY_METRICS_ENABLED=true
HELLO_SALES_OBSERVABILITY_METRICS_ENDPOINT_ENABLED=true
HELLO_SALES_OBSERVABILITY_TRACING_ENABLED=true
HELLO_SALES_OBSERVABILITY_TRACING_EXPORTER=otlp
HELLO_SALES_OBSERVABILITY_TRACING_OTLP_ENDPOINT=http://otel-collector.hello-sales-observability.svc.cluster.local:4318/v1/traces
```

If you need auth headers for the collector later:

```env
HELLO_SALES_OBSERVABILITY_TRACING_OTLP_HEADERS=authorization=Bearer your-token
```

Do not point the app directly at Tempo, Loki, or Grafana.
Point it at the collector.

## Step 8: Validate The Stack End To End

After deployment, check these in order.

### Backend

- `/metrics` responds
- `/api/system/diagnostics` shows tracing enabled and the OTLP endpoint

### Collector

- collector pod is ready
- collector logs do not show exporter loop failures

### Prometheus

- target `hello-sales-backend` is `UP`
- target `otel-collector` is `UP`
- rules are loaded

### Loki

- queries return backend logs

### Tempo

- traces appear after generating test traffic

### Grafana

- datasources are healthy
- the starter dashboard loads

## Step 9: Run A Basic Smoke Test

Generate a little real traffic:

1. hit `/api/health/liveness`
2. hit `/api/health/readiness`
3. trigger a worker run or diagnostic job
4. trigger one intentional error path in a safe environment

Then verify:

- metrics increase in Prometheus
- logs appear in Loki
- traces appear in Tempo
- the dashboard panels move

If only one signal arrives, do not keep going. Fix the pipeline before building more on top of it.

## Step 10: Understand The Starter Dashboards And Alerts

This repo now includes:

- starter Grafana dashboard provisioning
- starter Prometheus alert rules

Dashboard focus:
- request rate by route
- request latency by route
- active background tasks
- active worker runs

Alert focus:
- collector down
- elevated HTTP failure rate
- background task failures
- worker run concurrency stuck high

These are starter alerts. They are intentionally conservative and generic.

You should tune them after observing real traffic.

## Step 11: What To Watch Operationally

If you are new to operating monitoring infrastructure, watch these first:

- **Collector health**
  - if the collector fails, traces and logs can disappear or back up

- **Prometheus disk usage**
  - time-series growth is easy to underestimate

- **MinIO capacity**
  - Loki and Tempo will push object growth over time

- **Loki query latency**
  - if logs become slow to query, users stop trusting the system

- **Grafana auth and exposure**
  - Grafana is an operator entrypoint; do not expose it casually

## Step 12: First Failure Drill

Run one deliberate drill in `staging`.

Suggested drill:

1. scale the collector deployment to `0`
2. generate traffic from HelloSales
3. verify:
   - Prometheus still scrapes backend `/metrics`
   - traces stop arriving
   - collector alert fires
4. restore the collector
5. verify recovery

That drill teaches the team more than reading docs.

## Step 13: What Is Still Not Finished Automatically

This repo gives you a strong base, but you still need environment-specific work:

- real secret delivery
- real TLS
- real DNS
- real storage-class choices
- possible multi-replica or HA topology
- backup/restore testing for MinIO and Prometheus
- alert delivery routing such as email, Slack, PagerDuty, or Opsgenie

If you skip those, you have a deployment, not an operating model.

## Recommended First Real Rollout

If this is your first hosted monitoring stack, do this:

1. deploy `dev` overlay
2. validate all signals
3. deploy `staging` overlay
4. run at least one failure drill
5. tune retention and alerts
6. only then create the `prod` rollout

Do not start in production just because the manifests exist.

## Commands You Will Use Most

Render manifests:

```bash
kubectl kustomize backend/ops/observability/production/kubernetes/overlays/staging
```

Apply manifests:

```bash
kubectl apply -k backend/ops/observability/production/kubernetes/overlays/staging
```

Check pods:

```bash
kubectl get pods -n hello-sales-observability
```

Check logs:

```bash
kubectl logs -n hello-sales-observability deploy/otel-collector
kubectl logs -n hello-sales-observability deploy/prometheus
kubectl logs -n hello-sales-observability deploy/grafana
kubectl logs -n hello-sales-observability statefulset/loki
kubectl logs -n hello-sales-observability statefulset/tempo
kubectl logs -n hello-sales-observability statefulset/minio
```

Check services:

```bash
kubectl get svc -n hello-sales-observability
```

## Final Advice

The hardest part of self-hosted monitoring is not getting the first dashboard to appear.
The hardest part is keeping the system understandable once it has been running for months.

Keep these rules:

- keep retention explicit
- keep storage separate from the application database
- keep alerts few and meaningful at first
- keep dashboards narrow and operational
- keep the collector as the app’s telemetry boundary
- test one failure drill before you trust the stack

If you want, the next useful step is for me to add:
- Alertmanager with Slack or email routing
- environment-specific TLS and ingress patches for your actual cluster
- a `kubectl` rollout checklist with exact commands for `dev`, `staging`, and `prod`

## Appendix: Middle Ground Between Self-Hosted And Fully Managed

If you do not want to deal with VMs, Kubernetes, storage classes, object storage, backups, and network policies yourself, there is a middle ground.

The most practical middle-ground model is:

- use a managed observability backend for raw logs, metrics, and traces
- keep your custom internal dashboard in your own app
- keep the backend export model in HelloSales the same

That means:
- your app still emits OTLP traces, Prometheus-style metrics, and structured logs
- you still control your operator UX
- you stop operating Loki, Tempo, Prometheus, MinIO, and Grafana yourself

### What “Middle Ground” Usually Means

There are three common options:

1. **Managed SaaS**
   - the vendor runs everything
   - you send telemetry to them
   - least operational work

2. **Managed In Your Cloud Account**
   - the vendor operates the platform, but it runs in your AWS or GCP account
   - less operational work than self-hosting
   - better data residency and cloud-commit alignment

3. **Serverless Observability**
   - you do not manage infrastructure
   - you pay mainly for ingest, storage, and usage
   - simplest onboarding path for small teams

### Cost Bands

The numbers below are rough planning guidance, not quotes.

Use these bands:
- `£` = usually under about `£100/month`
- `££` = usually about `£100` to `£500/month`
- `£££` = usually about `£500` to `£2,000/month`
- `££££` = usually above `£2,000/month`

These estimates depend heavily on:
- number of hosts or containers
- log volume in GB per month
- trace volume in GB per month
- metric cardinality
- retention
- whether you use curated APM products instead of only raw telemetry storage

### Option 1: Grafana Cloud

Best for:
- teams that like the Grafana, Prometheus, Loki, and Tempo model
- teams that want very low operational burden
- teams that still want Grafana as the main operator workbench

Rough cost band:
- small team / low volume: `£` to low `££`
- growing team / moderate volume: `££` to `£££`
- heavy retained telemetry or enterprise support: `£££` to `££££`

Why:
- Grafana Cloud’s public pricing currently shows a `$19/month` platform fee on Pro plans, plus telemetry pricing such as `$6.50 per 1k metrics series` and `$0.50 per GB` for logs and traces, and host-hour pricing for curated monitoring products.
- In rough GBP terms, the platform entry point is low, but usage can scale quickly if you keep lots of high-cardinality metrics or ingest lots of logs.

Planning heuristic:
- tiny stack: roughly `£15` to `£80/month`
- moderate stack: roughly `£100` to `£400/month`
- larger stack with real retention and more hosts: `£500+/month`

Operational burden:
- very low

Trade-off:
- less control over raw storage and infra topology than self-hosting

### Option 2: Grafana BYOC

Best for:
- teams that want a managed platform but care where the data plane runs
- teams with existing AWS or GCP commitments
- larger organizations that want managed operations without pure multi-tenant SaaS

Rough cost band:
- usually `££££`

Why:
- Grafana positions BYOC as an enterprise offering
- Grafana’s public pricing and product pages show enterprise minimum commitments and BYOC as part of enterprise deployment flexibility

Planning heuristic:
- assume this is not the cheap path
- think in annual enterprise budget, not hobby or early-startup monthly budget

Operational burden:
- low to medium

Trade-off:
- still much less operational work than self-hosting
- but it is typically meant for larger spend and procurement cycles

### Option 3: Elastic Observability Serverless

Best for:
- teams that want logs, metrics, and traces in one serverless platform
- teams that want less infrastructure ownership
- teams comfortable with Elastic’s query and storage model

Rough cost band:
- small to moderate footprint: `£` to `££`
- growing footprint: `££` to `£££`

Why:
- Elastic’s current serverless observability pricing is usage-based around ingest, retention, and transfer
- official pricing currently describes ingest pricing “as low as” around `$0.07/GB`, with retention priced separately

Planning heuristic:
- very small footprint: tens of pounds per month
- moderate team with meaningful logs/traces: low hundreds per month
- heavier search and retention: hundreds to low thousands

Operational burden:
- very low

Trade-off:
- less infra work, but you are buying into Elastic’s platform model rather than the Grafana ecosystem

### Option 4: Datadog

Best for:
- teams that want a very polished all-in-one commercial platform
- teams that are comfortable paying more to avoid operational complexity

Rough cost band:
- moderate use: `£££`
- broad use across infra + APM + logs: `£££` to `££££`

Why:
- Datadog’s public pricing and pricing FAQ show separate pricing dimensions for infrastructure, APM, and logs
- the platform is strong, but it is commonly one of the more expensive options once you turn on multiple products at real scale

Planning heuristic:
- if you use only a little, it can be manageable
- if you use infra monitoring, APM, and meaningful log ingestion together, expect the bill to climb fast

Operational burden:
- very low

Trade-off:
- excellent usability
- often the most painful cost curve

### What I Would Recommend For You

Given this repo and what has already been built:

1. If you want the **least ops burden** while keeping a custom dashboard:
   - use **Grafana Cloud**
   - keep your own custom operator dashboard in HelloSales
   - use Grafana for raw telemetry exploration

2. If you want **managed but still closer to “my cloud, my account”**:
   - evaluate **Grafana BYOC**
   - do this only if your scale or procurement model justifies enterprise spend

3. If you want **simple serverless ingestion and do not care about the Grafana ecosystem specifically**:
   - evaluate **Elastic Observability Serverless**

### Practical Decision Rule

Choose:

- **self-hosted** if control matters more than time
- **managed backend + your own dashboard** if you want the best balance
- **fully managed SaaS only** if you want the fastest path and can live with the vendor’s UI as your primary operator surface

For most teams in your position, the best balance is:

- managed telemetry backend
- your own dashboard for your own workflows
- no self-operated observability infrastructure

### Pricing Caveat

These estimates are planning ranges only.

Vendor pricing changes, exchange rates change, and telemetry bills are highly sensitive to actual usage.

Before committing, take one week of real or representative telemetry volume from:
- `/metrics`
- expected log GB/day
- expected trace GB/day

Then price the options from the vendor calculators or sales teams using your real numbers.
