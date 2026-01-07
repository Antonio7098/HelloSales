# HelloSales

Sales management platform with AI-powered coaching capabilities.

## Quick Start

```bash
# 1. Start infrastructure
make up

# 2. Install dependencies
make install-backend  # Backend venv created automatically
make install-mobile   # Mobile npm install

# 3. Configure environment
cd backend && cp .env.example .env
# Edit .env with your API keys

# 4. Run migrations
make migrate-db

# 5. Start services (separate terminals)
make backend   # Terminal 1: http://localhost:8000
make mobile    # Terminal 2: http://localhost:8002
```

## Project Overview

HelloSales is a full-stack sales management platform combining:

- **Backend**: FastAPI with PostgreSQL + Redis
- **Mobile**: React Native with Expo Router
- **AI**: Real-time conversational agents with multiple LLM providers

### Key Features

- **Sales Playbook**: Manage clients, products, strategies
- **Practice Sessions**: AI-powered sales coaching
- **Organization Management**: WorkOS SSO integration
- **Multi-provider AI**: Groq, Gemini, Deepgram, Google

## Architecture

```
┌─────────────────────────────────────────────────┐
│            HelloSales Platform             │
└─────────────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
   ┌──────┐   ┌──────┐   ┌────────┐
   │Mobile │   │Backend│   │WorkOS  │
   │Expo  │   │FastAPI│   │   SSO  │
   └──────┘   └──────┘   └────────┘
        │            │
        │    ┌───────┴───────┐
        │    │               │
        │    ▼               ▼
        │ ┌──────┐      ┌──────┐
        │ │Postgres│      │Redis  │
        │ │:5434  │      │:6380  │
        │ └──────┘      └──────┘
        │
        └──────────┐
                   ▼
            ┌──────────┐
            │   AI     │
            │Providers │
            │(Groq/    │
            │Deepgram/  │
            │Google)    │
            └──────────┘
```

**See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture.**

## Project Structure

```
HelloSales/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/        # HTTP & WebSocket endpoints
│   │   ├── ai/         # AI pipeline & agents
│   │   ├── auth/       # WorkOS authentication
│   │   ├── models/     # SQLAlchemy ORM
│   │   ├── schemas/    # Pydantic schemas
│   │   └── services/   # Business logic
│   ├── migrations/      # Alembic migrations
│   ├── tests/           # Test suite
│   └── pyproject.toml   # Python dependencies
│
├── mobile/               # React Native app
│   ├── app/
│   │   ├── _components/ui/   # Design system
│   │   ├── screens/         # Screen components
│   │   ├── stores/          # Zustand state
│   │   ├── services/        # API clients
│   │   └── theme/           # Design tokens
│   └── package.json
│
├── docker-compose.yml   # Infrastructure (Postgres, Redis)
├── Makefile            # Common commands
├── setup.sh           # Automated setup
└── README.md
```

## Development

### Prerequisites

- **Backend**:
  - Python 3.11+
  - Docker & Docker Compose

- **Mobile**:
  - Node.js 18+
  - Expo CLI

### Common Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make up` | Start PostgreSQL + Redis containers |
| `make down` | Stop infrastructure |
| `make backend` | Start backend server |
| `make mobile` | Start mobile dev server |
| `make install-backend` | Install backend dependencies |
| `make install-mobile` | Install mobile dependencies |
| `make migrate-db` | Run database migrations |
| `make test-backend` | Run backend tests |
| `make lint-backend` | Run backend linting |
| `make shell-db` | Open PostgreSQL shell |

### Environment Configuration

**Backend** (`backend/.env`):
```env
# Database
DATABASE_URL=postgresql+asyncpg://hellosales:hellosales_dev@localhost:5434/hellosales

# Redis
REDIS_URL=redis://localhost:6380/0

# Authentication
WORKOS_CLIENT_ID=your_workos_client_id
WORKOS_API_KEY=your_workos_api_key

# AI Providers
GROQ_API_KEY=your_groq_key
DEEPGRAM_API_KEY=your_deepgram_key
GOOGLE_API_KEY=your_google_key
```

**Mobile** (`mobile/.env` or `app.config.ts`):
```typescript
extra: {
  apiUrl: process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000'
}
```

## Testing

### Backend Tests

```bash
cd backend
./venv/bin/pytest -xvs tests/
```

### Mobile Tests

```bash
cd mobile
npm test  # (if configured)
```

## Documentation

- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md) - System design & protocols
- **Backend**: [backend/README.md](backend/README.md) - API & development guide
- **Mobile**: [mobile/README.md](mobile/README.md) - Component library & setup
- **Quick Start**: [QUICKSTART.md](QUICKSTART.md) - Getting started guide

## API Documentation

Once backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## License

See LICENSE file for details.
