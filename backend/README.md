# HelloSales Backend

FastAPI backend for HelloSales sales management platform.

## Overview

The backend provides:
- REST API for CRUD operations
- WebSocket for real-time communication
- AI pipeline with multi-provider support
- WorkOS SSO authentication
- Organization multi-tenancy

## Quick Start

```bash
# From project root
make up                    # Start PostgreSQL + Redis
cd backend
./venv/bin/pip install -e ".[dev]"  # Install dependencies
cp .env.example .env    # Configure environment
./venv/bin/alembic upgrade head  # Run migrations
./venv/bin/uvicorn app.main:app --reload --port 8000  # Start server
```

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application entry
│   ├── config.py               # Pydantic settings
│   ├── database.py             # SQLAlchemy async setup
│   ├── logging_config.py       # JSON logging configuration
│   │
│   ├── api/                    # API Layer
│   │   ├── http/              # REST endpoints
│   │   │   ├── dependencies.py  # Auth & org context
│   │   │   ├── auth.py          # Authentication routes
│   │   │   ├── profile.py       # User profile
│   │   │   ├── sailwind.py      # Sales playbook (main domain)
│   │   │   ├── orgs.py         # Organization management
│   │   │   ├── feedback.py      # User feedback
│   │   │   ├── legal.py         # Terms/privacy pages
│   │   │   └── admin/          # Admin endpoints
│   │   │
│   │   └── ws/                # WebSocket layer
│   │       ├── endpoint.py       # WebSocket handler (app/main.py:817)
│   │       ├── manager.py        # Connection manager
│   │       ├── router.py        # Message routing
│   │       ├── projector.py      # Response streaming
│   │       └── handlers/        # Message handlers
│   │           ├── auth.py      # Authentication handler
│   │           ├── chat.py      # Chat messages
│   │           ├── voice.py     # Voice/audio messages
│   │           ├── session.py   # Session management
│   │           └── ...
│   │
│   ├── models/                  # SQLAlchemy ORM
│   │   ├── user.py             # Users table
│   │   ├── session.py          # Sessions table
│   │   ├── interaction.py      # Interactions (messages) table
│   │   ├── organization.py    # Organizations table
│   │   ├── sailwind_playbook.py # Sales domain tables
│   │   ├── skill.py           # Skills & assessments
│   │   └── observability.py  # Pipeline runs & events
│   │
│   ├── schemas/                 # Pydantic schemas
│   │   ├── organization.py    # Organization schemas
│   │   ├── sailwind_playbook.py # Sales domain schemas
│   │   ├── sailwind_practice.py # Practice sessions
│   │   ├── feedback.py       # Feedback schemas
│   │   └── ...
│   │
│   ├── ai/                     # AI Pipeline
│   │   ├── providers/          # External AI providers
│   │   │   ├── llm/           # Groq, Gemini, OpenRouter
│   │   │   │   ├── groq.py     # Groq LLM client
│   │   │   │   ├── gemini.py   # Google Gemini
│   │   │   │   ├── openrouter.py
│   │   │   │   └── stub.py     # Test stub
│   │   │   ├── stt/           # Speech-to-text
│   │   │   │   ├── deepgram.py      # Deepgram STT
│   │   │   │   ├── deepgram_flux.py
│   │   │   │   ├── google.py        # Google STT
│   │   │   │   └── groq_whisper.py  # Groq Whisper
│   │   │   └── tts/           # Text-to-speech
│   │   │       ├── google.py    # Google TTS
│   │   │       └── gemini.py   # Gemini Flash TTS
│   │   │
│   │   ├── substrate/          # Pipeline architecture
│   │   │   ├── protocols/      # Agent, Worker, Dispatcher interfaces
│   │   │   │   ├── agent_protocol.py  # Agent interface
│   │   │   │   ├── worker.py       # Worker interface
│   │   │   │   ├── dispatcher.py   # Dispatcher interface
│   │   │   │   └── routing.py      # Router interface
│   │   │   ├── stages/        # Pipeline stages
│   │   │   │   ├── base.py        # Stage base class
│   │   │   │   ├── guardrails.py  # Safety checks
│   │   │   │   ├── policy.py       # Authorization
│   │   │   │   ├── context.py      # Context building
│   │   │   │   └── agent.py       # Agent stage
│   │   │   ├── tools/         # Tool system
│   │   │   │   ├── executor.py    # Tool executor
│   │   │   │   └── registry.py    # Tool registry
│   │   │   ├── agent/         # Agent implementations
│   │   │   │   └── context_snapshot.py  # Context snapshot
│   │   │   ├── projector.py    # Response streaming
│   │   │   ├── observability.py  # Metrics collection
│   │   │   └── orchestrator.py # Pipeline orchestration
│   │   │
│   │   ├── pipelines/          # Pipeline definitions
│   │   │   └── definitions.py  # Voice/chat pipeline configs
│   │   │
│   │   ├── agents/            # Conversational agents
│   │   │   └── conversational.py  # Main chat agent
│   │   │
│   │   └── validation/        # Input validation
│   │
│   ├── auth/                   # Authentication
│   │   ├── workos.py          # WorkOS JWT verification
│   │   └── identity.py        # Identity claims normalization
│   │
│   ├── services/                # Business logic
│   │   ├── session_state.py  # Session management service
│   │   ├── events.py          # Event handling service
│   │   └── logging.py         # Logging service
│   │
│   └── exceptions.py            # Custom exceptions
│
├── migrations/                  # Alembic migrations
│   ├── versions/               # Migration scripts
│   └── env.py                # Alembic environment
│
├── tests/                      # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/           # Integration tests
│   └── conftest.py           # Pytest configuration
│
├── pyproject.toml              # Python dependencies
├── alembic.ini                 # Alembic configuration
├── Dockerfile                   # Docker image
└── supabase_schema.sql         # Initial database schema
```

## API Endpoints

### Base URL
- Development: `http://localhost:8000`

### REST Endpoints

#### Authentication
- `POST /api/v1/auth/verify` - Verify JWT token
- `GET /api/v1/auth/me` - Get current user

#### Profile
- `GET /api/v1/profile` - Get user profile
- `PATCH /api/v1/profile` - Update profile

#### Organization
- `GET /api/v1/orgs` - List organizations
- `GET /api/v1/orgs/{id}` - Get organization

#### Sailwind (Sales Playbook)
- `GET /api/v1/sailwind/clients` - List clients
- `POST /api/v1/sailwind/clients` - Create client
- `GET /api/v1/sailwind/clients/{id}` - Get client
- `PATCH /api/v1/sailwind/clients/{id}` - Update client
- `DELETE /api/v1/sailwind/clients/{id}` - Archive client

- `GET /api/v1/sailwind/products` - List products
- `POST /api/v1/sailwind/products` - Create product
- `GET /api/v1/sailwind/products/{id}` - Get product
- `PATCH /api/v1/sailwind/products/{id}` - Update product

- `GET /api/v1/sailwind/strategies` - List strategies
- `POST /api/v1/sailwind/strategies` - Create strategy
- `PATCH /api/v1/sailwind/strategies/{id}` - Update strategy

- `GET /api/v1/sailwind/my/rep-assignments` - My assignments
- `GET /api/v1/sailwind/my/practice-sessions` - My practice sessions
- `POST /api/v1/sailwind/practice-sessions` - Start practice

**Implementation**: `app/api/http/sailwind.py`

### WebSocket Endpoints

#### Connection
- `WS /ws` - WebSocket endpoint

#### Message Types

| Type | Handler | Description |
|------|----------|-------------|
| `auth` | `handlers/auth.py` | Authenticate connection |
| `ping` | `handlers/ping.py` | Keep-alive |
| `chat` | `handlers/chat.py` | Text messages |
| `voice` | `handlers/voice.py` | Voice/audio messages |
| `session` | `handlers/session.py` | Session management |
| `feedback` | `handlers/feedback.py` | User feedback |
| `pipeline` | `handlers/pipeline.py` | Pipeline control |

**Implementation**: `app/api/ws/router.py`, `app/api/ws/endpoint.py:817`

### WebSocket Message Format

```typescript
{
  type: string;      // Message type
  payload?: any;     // Message payload
}
```

#### Authentication Flow

```javascript
// 1. Connect
const ws = new WebSocket('ws://localhost:8000/ws');

// 2. Send auth
ws.send(JSON.stringify({
  type: 'auth',
  payload: {
    token: 'workos_jwt_or_dev_token',
    platform: 'web' | 'native'
  }
}));

// 3. Receive response
{
  "type": "auth.success",
  "payload": {
    "userId": "uuid",
    "sessionId": "uuid | null",
    "orgId": "uuid"
  }
}
```

## Authentication

### WorkOS SSO

All requests require a valid WorkOS JWT with `org_id` claim.

**Development Shortcut**: Use token `"dev_token"` for testing.

**Implementation**:
- JWT verification: `app/auth/workos.py`
- Identity claims: `app/auth/identity.py:10-17`
- Auth dependency: `app/api/http/dependencies.py:12-30`

### Authorization

Role-based access control:
- `admin` - Full access to organization resources
- `member` - Limited access

**Implementation**: `app/api/http/sailwind.py:52-69`

## AI Pipeline

### Pipeline Stages

```
Request → [Guardrails] → [Policy] → [Enrich] → [Agent] → [Tools] → [Projector] → Response
```

**Files**:
- Guardrails: `app/ai/substrate/stages/guardrails.py`
- Policy Gateway: `app/ai/substrate/policy/gateway.py`
- Context Enrichment: `app/ai/substrate/stages/context.py`
- Agent: `app/ai/substrate/stages/agent.py`
- Tool Executor: `app/ai/substrate/tools/executor.py`
- Projector: `app/api/ws/projector.py`

### Agent Protocol

Agents implement the `Agent` interface:

```python
class Agent(ABC):
    id: str
    services: tuple[str, ...]
    capabilities: tuple[str, ...]

    async def plan(self, snapshot: ContextSnapshot) -> Plan:
        """Generate response plan"""
        ...
```

**Interface**: `app/ai/substrate/protocols/agent_protocol.py:40-22`

### Provider Configuration

LLM Providers (`app/ai/providers/llm/`):
- **Groq** (`groq.py`) - Primary LLM (Llama models)
- **Gemini** (`gemini.py`) - Google Gemini
- **OpenRouter** (`openrouter.py`) - Multi-provider gateway
- **Stub** (`stub.py`) - Test stub

STT Providers (`app/ai/providers/stt/`):
- **Deepgram** (`deepgram.py`) - Primary STT
- **Google** (`google.py`) - Google STT
- **Groq Whisper** (`groq_whisper.py`) - Groq Whisper API

TTS Providers (`app/ai/providers/tts/`):
- **Google** (`google.py`) - Google Neural TTS
- **Gemini Flash** (`gemini.py`) - Gemini Flash TTS

## Database

### Schema

Core tables:
- `users` - User accounts
- `organizations` - Organizations
- `organization_memberships` - User-org mapping
- `sessions` - Conversation sessions
- `interactions` - Messages
- `sailwind_clients` - Client records
- `sailwind_products` - Products
- `sailwind_strategies` - Sales strategies
- `pipeline_runs` - AI pipeline executions
- `pipeline_events` - Pipeline events

**Full Schema**: `supabase_schema.sql`

### Migrations

```bash
# Apply migrations
./venv/bin/alembic upgrade head

# Create new migration
./venv/bin/alembic revision -m "description"

# Rollback
./venv/bin/alembic downgrade -1
```

**Config**: `alembic.ini`

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL async URL | Yes |
| `REDIS_URL` | Redis URL | Yes |
| `WORKOS_CLIENT_ID` | WorkOS client ID | Yes (prod) |
| `WORKOS_API_KEY` | WorkOS API key | Yes (prod) |
| `WORKOS_ISSUER` | Token issuer | No |
| `GROQ_API_KEY` | Groq LLM key | Yes (AI) |
| `DEEPGRAM_API_KEY` | Deepgram STT key | Yes (AI) |
| `GOOGLE_API_KEY` | Google API key | Yes (AI) |
| `LOG_LEVEL` | Logging level | No |

**Config**: `app/config.py`, `.env.example`

## Testing

```bash
# Run all tests
./venv/bin/pytest -xvs tests/

# Run unit tests
./venv/bin/pytest -xvs tests/unit/

# Run integration tests
./venv/bin/pytest -xvs tests/integration/

# Run specific test
./venv/bin/pytest -xvs tests/integration/test_websocket.py
```

## Development

### Linting & Formatting

```bash
# Lint
./venv/bin/ruff check .

# Format
./venv/bin/ruff format .
```

### Logging

Structured JSON logging:
- Request ID tracking
- Service identification
- Contextual metadata
- Configurable levels

**Config**: `app/logging_config.py`

## Deployment

### Docker

```bash
# Build image
docker build -t hellosales-backend .

# Run container
docker run -p 8000:8000 hellosales-backend
```

### Production Considerations

- Use Gunicorn with Uvicorn workers
- Configure PostgreSQL connection pooling
- Set up Redis for caching
- Use environment-specific WorkOS keys
- Enable HTTPS with proper TLS certificates
