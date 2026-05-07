# HelloSales Backend Scaffold

> **Note**: Project overview lives in the root [README.md](../README.md).

## Prerequisites

- **Python 3.12+**
- **PostgreSQL 17+** (via Docker for local dev)
- **Docker** & Docker Compose

This backend scaffold is Postgres-first in development and production.

## Project Structure

```
backend/
├── src/hello_sales_backend/
│   ├── api/              # HTTP routes
│   ├── modules/           # Bounded context modules
│   ├── platform/         # Platform seams (llm, db, observability)
│   ├── workers/          # Background workers
│   ├── smoke/           # Smoke test harness
│   └── app.py           # FastAPI app factory
├── scripts/              # Dev and build scripts
│   ├── smoke.py        # Smoke test runner
│   ├── verify_postgres.py
│   └── scaffold_module.py
├── ops/observability/    # Self-hosted observability
├── Makefile            # Dev commands
├── pyproject.toml      # Python dependencies
└── .env.example      # Environment template
```

See `backend/docs/codebase-map.md` for detailed package breakdown.

## What Works / What Doesn't

### Works
- FastAPI app factory with async SQLAlchemy 2.0+ runtime
- OpenAI-compatible LLM provider seam (Groq, OpenAI, etc.)
- Stageflow workflow runtime boundary
- Request context middleware with correlation IDs
- Health endpoints (`/api/system/health`, `/api/system/ready`)
- Async database migrations with Alembic
- Smoke tests with provider variants
- Prometheus metrics and OTLP tracing
- Background task worker runtime

### Doesn't Work Yet
- Real authentication (dev provider only)
- Product-specific domain modules
- Webhook/callback surfaces

## Development Database

For the full Docker-based local stack, including Postgres, backend, `frontend-draft`,
Grafana, Prometheus, Loki, Tempo, MinIO, and the OTEL collector, from the root directory:

```bash
make dev-up
```

Useful companion commands:

```bash
make dev-logs
make dev-ps
make dev-down
```

Default local URLs:

- frontend-draft: `http://localhost:5173`
- backend API: `http://localhost:8000`
- Grafana: `http://localhost:3001`
- Prometheus: `http://localhost:9090`
- Loki: `http://localhost:3100`
- Tempo: `http://localhost:3200`
- MinIO console: `http://localhost:9001`

Default application database URL:

```text
postgresql+asyncpg://hello_sales:hello_sales@localhost:5432/hello_sales
```

Start local Postgres:

```bash
cd backend
make dev-db-up
```

Stop local Postgres:

```bash
make dev-db-down
```

Tail database logs:

```bash
make dev-db-logs
```

Verify the database is reachable:

```bash
make verify-db
```

## Environment

Copy the example environment file if you want local overrides:

```bash
cp .env.example .env
```

The application reads settings from `HELLO_SALES_*` environment variables.
Required for LLM provider:

```bash
HELLO_SALES_GENERIC_AGENT_PROVIDER=groq
HELLO_SALES_GENERIC_AGENT_MODEL=openai/gpt-oss-20b
HELLO_SALES_GROQ_API_KEY=sk-...
```

Optional settings:

```bash
HELLO_SALES_GENERIC_AGENT_TIMEOUT_SECONDS=30
HELLO_SALES_GENERIC_AGENT_BASE_URL=  # Override endpoint
HELLO_SALES_DATABASE_URL=  # Override DB connection
HELLO_SALES_CORS_ALLOWED_ORIGINS=["http://localhost:5173"]
```

## Smoke Tests

List available smoke suites:

```bash
python3 scripts/smoke.py --list
```

Run generic-agent provider smoke:

```bash
make smoke
```

Run targeted provider-backed smoke suites:

```bash
make smoke-provider-baseline
make smoke-provider-observer
make smoke-provider-append
make smoke-provider-approval
make smoke-provider-events
make smoke-provider-read-catalog
make smoke-provider-entity-mutation
make smoke-provider-worker
```

## Migrations

Apply migrations:

```bash
make migrate
```

Create a new migration:

```bash
make revision message="add task table"
```

## Tests

Tests use temporary SQLite databases for fast local execution.
That is intentional:

- development and migrations should target Postgres
- tests may use SQLite where the test scope is only scaffold validation

The smoke harness is centralized under `hello_sales_backend.smoke`
and is exposed through `scripts/smoke.py`.

Run tests:

```bash
make test
```

Optional Postgres-backed integration tests:

```bash
HELLO_SALES_RUN_POSTGRES_TESTS=1 python3 -m pytest tests/postgres -q
```

Run type checking:

```bash
make mypy
```

## Module Scaffold Generator

Create a new bounded-context module from the local templates:

```bash
python3 scripts/scaffold_module.py deals
```

Or after installing the package:

```bash
hello-sales-scaffold-module deals
```

This writes a new module under `src/hello_sales_backend/modules/`.

## Current Scope

This scaffold currently provides:

- FastAPI app factory
- async SQLAlchemy runtime
- composition root
- Stageflow runtime boundary
- neutral `platform/llm/` provider seam with an OpenAI-compatible adapter
- request context middleware
- request, provider, workflow, and task failure logging
- background task runner
- health endpoints
- diagnostics endpoint
- a sample module (`system`)
- an operational jobs module with a diagnostic workflow
- an operational `agent-runs` module
- an operational `worker-runs` module

## Troubleshooting

### "connection refused" to database
- Ensure Postgres is running: `docker compose ps`
- Wait for healthcheck (up to 100s): `make dev-db-up`
- Check logs: `make dev-db-logs`

### Smoke tests fail with "provider not configured"
- Set `HELLO_SALES_GENERIC_AGENT_PROVIDER` and `HELLO_SALES_GROQ_API_KEY` in `.env`

### Import errors
- Ensure `PYTHONPATH=src` or install package: `pip install -e .`

### Port conflicts
- 8000 (backend), 5432 (postgres), 5173 (frontend-draft)

### OTLP export failing
- Check collector is running: `docker compose ps otel-collector`
- Verify endpoint: `HELLO_SALES_OBSERVABILITY_TRACING_OTLP_ENDPOINT`

## Related Docs

- [backend/docs/README.md](docs/README.md) - Technical documentation index
- [backend/docs/architecture-philosophy.md](docs/architecture-philosophy.md) - Architectural principles
- [backend/docs/runtime-overview.md](docs/runtime-overview.md) - Runtime architecture
- [backend/docs/agent-runtime.md](docs/agent-runtime.md) - Agent runtime details
- [backend/docs/testing-and-operations.md](docs/testing-and-operations.md) - Testing and ops
- [backend/docs/observability-hosting-guide.md](docs/observability-hosting-guide.md) - Self-hosted observability# trigger
trigger
trigger
trigger
trigger
trigger
trigger
