# HelloSales

Pre-brief scaffold for a sales application, built according to the operational contract defined in `ops/operational-contract/pre-brief-scope.md`.

## Architecture

```
HelloSales/
├── backend/          # Python/FastAPI backend scaffold
├── frontend/         # React frontend scaffold
└── ops/              # Operational contracts and processes
```

## Pre-Brief Scope

This project is built before the product brief is complete. Per the pre-brief scope contract:

- **Allowed**: Foundation work, scaffolding, operational infrastructure, generic patterns
- **Deferred**: Product-specific domain logic, real bounded contexts, feature commitments

See `ops/operational-contract/pre-brief-scope.md` for the full contract and requirements.

## Getting Started

### Root Commands

```bash
make dev-up          # Start full local stack (Postgres, backend, frontend-draft, observability)
make dev-down        # Stop local stack
make dev-logs        # View logs
make dev-ps          # Show running containers
```

### Backend

See `backend/README.md` for full backend documentation.

```bash
cd backend
make verify-db       # Verify database connection
make migrate         # Apply migrations
make smoke           # Run smoke tests
```

### Frontend

See `frontend/README.md` for full frontend documentation.

```bash
cd frontend
npm install
npm run dev
```

## Local Services

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy (async), Alembic, Stageflow
- **Frontend**: React, TypeScript, Vite
- **Database**: PostgreSQL
- **Observability**: Grafana, Prometheus, Loki, Tempo, OpenTelemetry