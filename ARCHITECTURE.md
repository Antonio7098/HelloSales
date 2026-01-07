# HelloSales Architecture

## Overview

HelloSales is a sales management platform with AI-powered coaching capabilities. The system consists of:

- **Backend**: FastAPI Python server with PostgreSQL + Redis
- **Mobile**: React Native app with Expo Router
- **AI Pipeline**: Multi-stage agent system for real-time coaching

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HelloSales System                          │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Mobile     │    │   Backend    │    │  WorkOS SSO  │
│   (Expo)    │    │  (FastAPI)   │    │             │
└──────────────┘    └──────────────┘    └──────────────┘
        │                     │                     │
        │                     │                     │
        │              ┌──────┴──────┐              │
        │              │             │              │
        │              ▼             ▼              │
        │       ┌─────────┐  ┌─────────┐        │
        │       │Postgres │  │  Redis  │        │
        │       │  (5434) │  │ (6380)  │        │
        │       └─────────┘  └─────────┘        │
        │                                     │
        │                                     │
        ▼                                     ▼
┌─────────────────────────────────────────────────────────┐
│              AI Providers (External)              │
├─────────────────────────────────────────────────────────┤
│ • Groq (LLM - chat/summarization)          │
│ • Deepgram (STT - speech-to-text)            │
│ • Google (TTS - text-to-speech)              │
└─────────────────────────────────────────────────────────┘
```

## Backend Architecture

### Layer Structure

```
backend/app/
├── main.py                 # FastAPI application entry
├── config.py               # Configuration management
├── database.py             # SQLAlchemy async setup
├── logging_config.py       # Structured JSON logging
│
├── api/                    # API Layer
│   ├── http/              # REST endpoints
│   │   ├── dependencies.py  # Auth & org context
│   │   ├── auth.py          # Authentication routes
│   │   ├── profile.py       # User profile
│   │   ├── sailwind.py      # Sales playbook
│   │   └── ...
│   │
│   └── ws/                # WebSocket layer
│       ├── endpoint.py       # WebSocket handler
│       ├── manager.py        # Connection management
│       ├── router.py        # Message routing
│       └── handlers/        # Message handlers
│           ├── auth.py
│           ├── chat.py
│           ├── voice.py
│           └── ...
│
├── models/                  # ORM Models
│   ├── user.py             # Users table
│   ├── session.py          # Sessions
│   ├── interaction.py      # Messages
│   ├── organization.py    # Organizations
│   └── observability.py  # Pipeline runs/events
│
├── schemas/                 # Pydantic schemas
│   ├── organization.py
│   ├── sailwind_playbook.py
│   └── ...
│
├── ai/                     # AI Pipeline
│   ├── providers/          # External AI providers
│   │   ├── llm/           # Groq, Gemini, OpenRouter
│   │   ├── stt/           # Deepgram, Google
│   │   └── tts/           # Google, Gemini
│   │
│   ├── substrate/          # Pipeline architecture
│   │   ├── protocols/      # Agent, Worker, Dispatcher
│   │   ├── stages/        # Pipeline stages
│   │   ├── tools/         # Tool system
│   │   └── agent/         # Agent implementations
│   │
│   ├── pipelines/          # Pipeline definitions
│   └── agents/            # Conversational agents
│
├── auth/                   # Authentication
│   ├── workos.py          # WorkOS JWT verification
│   └── identity.py        # Identity claims
│
└── services/                # Business logic
    ├── session_state.py    # Session management
    ├── events.py          # Event handling
    └── logging.py         # Logging service
```

### Request Flow

#### HTTP REST Request
```
Client → CORS Middleware → Auth Dependency → Router → Handler
                                    │
                                    ▼
                               Business Logic
                                    │
                                    ▼
                              Database/Redis
                                    │
                                    ▼
                               Response
```

#### WebSocket Connection
```
Client Connects → Manager → Router → Handler
                     │
                     ├─> Connection Tracking
                     ├─> Session Management
                     └─> Message Routing
                              │
                              ▼
                         AI Pipeline
                              │
                              ▼
                     Real-time Response
```

### AI Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Request Context                        │
│  (messages, user profile, skills, memory)          │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │   Dispatcher    │  ← Selects agent/behavior
              └─────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  Orchestrator   │  ← Manages stage execution
              └─────────────────┘
                        │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
    ┌────────┐  ┌────────┐  ┌────────┐
    │ Guard  │  │ Policy │  │ Enrich │
    │ rails  │  │Gateway │  │ ments  │
    └────────┘  └────────┘  └────────┘
        │           │           │
        └───────────┼───────────┘
                    │
                    ▼
            ┌──────────────┐
            │    Agent     │  ← LLM-powered planning
            └──────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
    ┌────────┐  ┌────────┐  ┌────────┐
    │  Tool  │  │ Artifact│  │ Action │
    │Executor│  │Emitter │  │System │
    └────────┘  └────────┘  └────────┘
        │           │           │
        └───────────┼───────────┘
                    │
                    ▼
              ┌──────────────┐
              │  Projector   │  ← Streams to client
              └──────────────┘
```

**Stages:**

1. **Guardrails** - Safety/A1 checks (content filtering)
2. **Policy Gateway** - Authorization & validation
3. **Context Enrichment** - Profile, skills, memory
4. **Agent** - LLM-powered planning & response
5. **Tool Executor** - Execute external actions
6. **Projector** - Stream responses to client

**Key Files:**
- `ai/substrate/stages/guardrails.py` - Safety checks
- `ai/substrate/stages/context.py` - Context building
- `ai/substrate/protocols/agent_protocol.py` - Agent interface
- `api/ws/projector.py` - Response streaming

## Mobile Architecture

### Layer Structure

```
mobile/
├── app/
│   ├── _components/         # UI Components
│   │   └── ui/           # Design system
│   │       ├── Box.tsx
│   │       ├── Button.tsx
│   │       ├── Card.tsx
│   │       ├── Text.tsx
│   │       ├── Screen.tsx
│   │       └── index.ts      # Component exports
│   │
│   ├── screens/            # Screen components
│   │   ├── ClientsScreen.tsx
│   │   ├── ProductsScreen.tsx
│   │   └── SalesRepsScreen.tsx
│   │
│   ├── stores/             # State management
│   │   └── index.ts       # Zustand store
│   │
│   ├── services/           # API clients
│   │   ├── api.ts         # HTTP client
│   │   └── adapters.ts    # WebSocket adapter (TODO)
│   │
│   ├── data/              # Mock data
│   │   └── mockData.ts
│   │
│   ├── theme/             # Design tokens
│   │   └── index.ts       # Colors, spacing, typography
│   │
│   ├── assets/            # Static assets
│   │   └── icons, images
│   │
│   └── _layout.tsx        # Root layout
│
├── services/               # Shared services
│   └── api.ts
│
└── package.json
```

### Component Hierarchy

```
Layout (ThemeProvider)
 └── Stack (Expo Router)
      └── Screens
            └── UI Components
                  └── Primitives (Box, Text, etc.)
```

### State Management

Using **Zustand** for global state:

```typescript
interface Store {
  clients: Client[];
  products: Product[];
  // ... other state
  actions: {
    setClients: (clients: Client[]) => void;
    // ... other actions
  };
}
```

File: `app/stores/index.ts`

## Database Schema

### Core Tables

#### Users & Auth
- `users` - User accounts (linked to WorkOS)
- `organizations` - Organization records
- `organization_memberships` - User ↔ Organization mapping

#### Sessions & Conversations
- `sessions` - Conversation sessions
- `interactions` - Messages/turns
- `messages` - Individual message content

#### Sales Domain (Sailwind)
- `sailwind_clients` - Client records
- `sailwind_products` - Product catalog
- `sailwind_client_archetypes` - Client templates
- `sailwind_product_archetypes` - Product templates
- `sailwind_strategies` - Sales strategies
- `sailwind_rep_assignments` - Sales rep assignments
- `sailwind_practice_sessions` - Training sessions

#### AI & Observability
- `skills` - Sales skill definitions
- `user_skills` - User skill tracking
- `skill_assessments` - Skill evaluations
- `pipeline_runs` - AI pipeline executions
- `pipeline_events` - Pipeline stage events
- `provider_calls` - External AI provider calls

**Schema File:** `backend/supabase_schema.sql`

## Communication Protocols

### REST API

**Base URL:** `http://localhost:8000`

**Authentication:** Bearer token (WorkOS JWT)

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/docs` | API documentation |
| GET | `/api/v1/sailwind/clients` | List clients |
| POST | `/api/v1/sailwind/clients` | Create client |
| GET | `/api/v1/sailwind/products` | List products |
| POST | `/api/v1/sailwind/products` | Create product |
| GET | `/api/v1/sailwind/strategies` | List strategies |
| POST | `/api/v1/sailwind/practice-sessions` | Start practice |

**Implementation:** `backend/app/api/http/sailwind.py`

### WebSocket Protocol

**Endpoint:** `ws://localhost:8000/ws`

#### Message Format

```typescript
{
  type: string;      // Message type (auth, chat, voice, etc.)
  payload?: any;     // Message payload
}
```

#### Connection Flow

1. **Connect**
   ```javascript
   const ws = new WebSocket('ws://localhost:8000/ws');
   ```

2. **Authenticate**
   ```javascript
   ws.send(JSON.stringify({
     type: 'auth',
     payload: {
       token: 'workos_jwt_or_dev_token',
       platform: 'web' | 'native'
     }
   }));
   ```

3. **Response**
   ```json
   {
     "type": "auth.success",
     "payload": {
       "userId": "uuid",
       "sessionId": "uuid | null",
       "orgId": "uuid"
     }
   }
   ```

4. **Chat**
   ```javascript
   ws.send(JSON.stringify({
     type: 'chat',
     payload: { content: 'Hello!' }
   }));
   ```

**Implementation:** `backend/app/api/ws/endpoint.py`, `backend/app/api/ws/router.py`

## Security

### Authentication (WorkOS)

1. User authenticates with WorkOS SSO
2. WorkOS issues JWT with `org_id` claim
3. Client sends JWT in requests
4. Backend verifies signature and claims
5. `EnterpriseOrgContext` created for request

**Key Files:**
- `backend/app/auth/workos.py` - JWT verification
- `backend/app/auth/identity.py` - Identity claims
- `backend/app/api/http/dependencies.py` - Auth dependency

### Authorization

- Role-based access control (admin, member)
- Organization-scoped queries
- Policy gateway enforces constraints

**Implementation:** `backend/app/api/http/dependencies.py:30-70`

## Deployment

### Development

```bash
# Infrastructure
make up

# Backend
cd backend && ./venv/bin/uvicorn app.main:app --reload --port 8000

# Mobile
cd mobile && npx expo start --port 8002
```

### Production Considerations

- **Backend**:
  - Gunicorn/Uvicorn with workers
  - PostgreSQL with connection pooling
  - Redis for caching
  - Environment-specific WorkOS keys

- **Mobile**:
  - EAS Build for iOS/Android
  - CodePush for OTA updates
  - Secure store for tokens

## Key Design Decisions

1. **Async/Await throughout** - Non-blocking I/O for performance
2. **WebSocket over HTTP polling** - Real-time bidirectional communication
3. **Separation of AI pipeline** - Modular, testable, swappable providers
4. **Organization multi-tenancy** - Data isolation per org
5. **Design system components** - Reusable, consistent UI
6. **Zustand for state** - Lightweight, no boilerplate

## Cross-Reference Guide

| Feature | Backend File | Mobile File |
|---------|--------------|--------------|
| Client CRUD | `app/api/http/sailwind.py:52-80` | `app/screens/ClientsScreen.tsx` |
| API Client | N/A | `services/api.ts` |
| WebSocket Handler | `app/api/ws/endpoint.py` | `services/adapters.ts` (TODO) |
| Auth Middleware | `app/api/http/dependencies.py` | `services/api.ts:20-32` |
| State Management | `app/services/session_state.py` | `app/stores/index.ts` |
| AI Agent | `app/ai/agents/conversational.py` | N/A |
| Agent Protocol | `app/ai/substrate/protocols/agent_protocol.py` | N/A |
| Message Router | `app/api/ws/router.py` | N/A |
| UI Theme | N/A | `app/theme/index.ts` |
