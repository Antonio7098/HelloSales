# HelloSales

A sales application, built according to the operational contracts defined in `ops/operational-contract/`.

## Architecture

```
HelloSales/
├── backend/          # Python/FastAPI backend
├── frontend/         # React frontend
└── ops/              # Operational contracts and processes
```

## Getting Started

### Root Commands

```bash
make dev-up          # Start full local stack (Postgres, backend, frontend, observability)
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