# HelloSales

Pre-brief scaffold for a sales application, built according to the operational contract defined in `ops/operational-contract/pre-brief-scope.md`.

## Prerequisites

- **Docker** & Docker Compose (latest)
- **Python 3.12+** (backend development)
- **Node.js 20+** (frontend development)
- **make** (for root commands)

## Architecture

```
HelloSales/
├── backend/          # Python/FastAPI backend scaffold
├── frontend/         # React frontend scaffold (main)
├── frontend-draft/   # React frontend (draft/pre-brief)
├── central-pulse/    # Central operation frontend
├── ops/              # Operational contracts and processes
└── docker-compose.dev.yml  # Local full-stack dev
```

## Pre-Brief Scope

This project is built before the product brief is complete. Per the pre-brief scope contract:

- **Allowed**: Foundation work, scaffolding, operational infrastructure, generic patterns
- **Deferred**: Product-specific domain logic, real bounded contexts, feature commitments

See `ops/operational-contract/pre-brief-scope.md` for the full contract and requirements.

## What Works / What Doesn't

### Works
- Full local stack via `make dev-up`
- Backend API with OpenAI-compatible LLM provider seam
- Frontend-draft and central-pulse running with proxy to backend
- Observability stack (Prometheus, Loki, Tempo, Grafana, MinIO)
- Database migrations with async SQLAlchemy
- Smoke tests with provider variants

### Doesn't Work Yet
- Production deployment (observability K8s manifests need customization)
- Real authentication (dev provider only)
- Product-specific domain modules (deals, contacts, etc.)

## Getting Started

### Root Commands

```bash
make dev-up          # Start full local stack (Postgres, backend, frontend-draft, central-pulse, minio, observability)
make dev-down        # Stop local stack
make dev-logs        # View logs
make dev-ps          # Show running containers
```

### Backend

See `backend/README.md` for full backend documentation.

```bash
cd backend
cp .env.example .env  # Configure required env vars
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
| Frontend-draft | http://localhost:5173 |
| Central-pulse | http://localhost:5174 |
| Backend API | http://localhost:8000 |
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |

## Tech Stack

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy (async), Alembic, Stageflow
- **Frontend**: React 19, TypeScript 5.9, Vite 7
- **Database**: PostgreSQL 17
- **Observability**: Grafana 11, Prometheus 3, Loki 3, Tempo 2, OpenTelemetry

## Troubleshooting

### Container fails to start
```bash
make dev-logs        # Check container logs
make dev-ps         # Check container status
```

### Database connection refused
- Wait for healthcheck: `pg_isready` runs every 5s with 20 retries
- Or check: `docker compose ps`

### Frontend not connecting to backend
- Ensure backend is healthy: `curl http://localhost:8000/api/system/health`
- Check `VITE_API_PROXY_TARGET` in docker-compose.dev.yml

### Port conflicts
- 5173/5174 (frontend), 8000 (backend), 5432 (postgres), 3001 (grafana)

## Related Docs

- `ops/operational-contract/pre-brief-scope.md` - Pre-brief scope contract
- `backend/README.md` - Backend quickstart
- `backend/docs/README.md` - Backend technical docs
- `frontend/README.md` - Frontend quickstart