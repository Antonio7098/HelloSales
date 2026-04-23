# HelloSales Backend Scaffold

This backend scaffold is Postgres-first in development and production.

The canonical technical documentation set for the backend lives in `backend/docs/`:
- `backend/docs/README.md`
- `backend/docs/runtime-overview.md`
- `backend/docs/codebase-map.md`
- `backend/docs/api-and-runtime-surfaces.md`
- `backend/docs/testing-and-operations.md`

## Development Database

For the full Docker-based local stack, including Postgres, backend, `frontend-draft`,
Grafana, Prometheus, Loki, Tempo, MinIO, and the OTEL collector, from the repo root run:

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

List available smoke suites:

```bash
python3 scripts/smoke.py --list
```

Run the generic-agent provider smoke:

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
make smoke-provider-worker
```

Apply migrations:

```bash
make migrate
```

Create a new migration:

```bash
make revision message="add task table"
```

## Environment

Copy the example environment file if you want local overrides:

```bash
cp .env.example .env
```

The application reads settings from `HELLO_SALES_*` environment variables.
The shared LLM provider path used by both agents and workers is configured with:

```bash
HELLO_SALES_GENERIC_AGENT_PROVIDER=groq
HELLO_SALES_GENERIC_AGENT_MODEL=openai/gpt-oss-20b
HELLO_SALES_GROQ_API_KEY=...
```

Optional:

```bash
HELLO_SALES_GENERIC_AGENT_TIMEOUT_SECONDS=30
HELLO_SALES_GENERIC_AGENT_BASE_URL=
```

## Tests

Tests currently provide their own explicit settings and use temporary SQLite databases for fast local execution.
That is intentional:

- development and migrations should target Postgres
- tests may use SQLite where the test scope is only scaffold validation

The smoke harness is centralized under `hello_sales_backend.smoke` and is exposed through `scripts/smoke.py`.

Run tests:

```bash
make test
```

Optional Postgres-backed integration test:

```bash
HELLO_SALES_RUN_POSTGRES_TESTS=1 python3 -m pytest tests/postgres -q
```

## Module Scaffold Generator

Create a new bounded-context module from the local templates:

```bash
python3 scripts/scaffold_module.py deals
```

If the package is installed, the equivalent CLI is:

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
