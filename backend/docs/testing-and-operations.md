# Testing And Operations

## Purpose
This document explains how the backend is verified and how to operate the scaffold during development.

## Test Layout

The backend test suite is split into four layers.

### `tests/unit/`
Owns fast unit verification for:
- auth and tool permission behavior
- generic agent runtime behavior
- worker runtime behavior
- provider adapters and provider registry
- analytics-query manifest, validator, risk, and redaction behavior
- task runner behavior
- smoke runner behavior
- module scaffold generator behavior

### `tests/integration/`
Owns integration verification for:
- auth API, middleware, callback/logout/session behavior, and protected routes
- app factory and app assembly
- composition overrides
- agent event stream behavior
- analytics-query wiring and failure translation
- error contract behavior
- worker-runs operational behavior and metrics visibility

### `tests/smoke/`
Owns high-signal smoke verification for:
- health surface
- agent-runs surface
- worker-runs surface
- jobs diagnostic flow
- system diagnostics and system status
- provider-backed smoke behavior, including the governed analytics-query path in the generic-agent provider suite
- voice primitive validation, segmentation, fake providers, diagnostics, and fake duplex state transitions

### `tests/postgres/`
Owns optional Postgres-backed verification for:
- readiness behavior against Postgres
- SQLAlchemy-backed agent store behavior

## Smoke Harness

The canonical smoke harness lives in:
- `src/hello_sales_backend/smoke/`
- `scripts/smoke.py`

The CLI entrypoint:
- lists registered smoke suites
- runs one named suite
- prints structured JSON results
- returns non-zero exit codes on failure or timeout

Current provider-backed suites include:
- `generic-agent-provider`
- `generic-agent-provider-baseline`
- `observer-agent-provider`
- `generic-agent-provider-append-turn`
- `generic-agent-provider-approval-boundary`
- `generic-agent-provider-event-stream`
- `generic-agent-provider` scenario `analytics_query_completion`
- `worker-provider-baseline`
- `voice-stt`
- `voice-tts`
- `voice-llm-to-tts`
- `voice-duplex`

## Development Operations

### Local Database
The backend is Postgres-first for development and production.

Common commands from `backend/`:
- `make dev-db-up`
- `make dev-db-down`
- `make dev-db-logs`
- `make verify-db`

### Migrations
Common commands:
- `make migrate`
- `make revision message="add task table"`

### Tests
Common commands:
- `make test`
- `HELLO_SALES_RUN_POSTGRES_TESTS=1 python3 -m pytest tests/postgres -q`

### Smoke Commands
Examples:
- `python3 scripts/smoke.py --list`
- `make smoke`
- `make smoke-provider-baseline`
- `make smoke-provider-observer`
- `make smoke-provider-append`
- `make smoke-provider-approval`
- `make smoke-provider-events`
- `make smoke-provider-worker`
- `python3 scripts/smoke.py voice-stt`
- `python3 scripts/smoke.py voice-tts`
- `python3 scripts/smoke.py voice-llm-to-tts`
- `python3 scripts/smoke.py voice-duplex`

The governed analytics-query smoke path uses the existing `generic-agent-provider` suite rather than a separate SQL-specific harness.
In test mode it seeds a bounded SQLite fixture before app startup so the conversational tool path can be exercised deterministically.
Voice smokes use fake providers and do not require external STT/TTS credentials.
Real-provider voice smoke is explicitly deferred until a provider adapter and credential source are selected.

## Environment Model

The backend reads runtime settings from `HELLO_SALES_*` environment variables.
Auth uses:
- `HELLO_SALES_AUTH_PROVIDER`
- `HELLO_SALES_AUTH_REQUIRED`
- `HELLO_SALES_WORKOS_CLIENT_ID`
- `HELLO_SALES_WORKOS_API_KEY`
- `HELLO_SALES_WORKOS_COOKIE_PASSWORD`
- `HELLO_SALES_WORKOS_REDIRECT_URI`
- `HELLO_SALES_FRONTEND_APP_URL`
- `HELLO_SALES_VOICE_STT_PROVIDER`
- `HELLO_SALES_VOICE_TTS_PROVIDER`
- `HELLO_SALES_VOICE_REALTIME_PROVIDER`
- `HELLO_SALES_VOICE_TURN_DETECTION_PROVIDER`
- `HELLO_SALES_VOICE_REQUIRED`

The generic-agent provider path uses provider-specific env such as:
- `GENERIC_AGENT_PROVIDER`
- `GENERIC_AGENT_MODEL`
- provider API key variables such as `GROQ_API_KEY`
- optional timeout/base-url overrides

## Current Operational Scope

The scaffold currently provides:
- FastAPI app factory
- async SQLAlchemy runtime
- composition root
- Stageflow runtime boundary
- provider-neutral auth with WorkOS as the first real adapter
- request auth middleware and explicit route permission dependencies
- neutral LLM substrate with an OpenAI-compatible adapter
- request context middleware
- request, provider, workflow, and task failure logging
- background task runner
- health endpoints
- diagnostics endpoint
- a governed analytics-query module and semantic YAML catalog path
- a system module
- an operational jobs module with a diagnostic workflow
- an agent-runs module exposing the generic agent runtime
- a worker-runs module exposing the worker runtime
- a voice module exposing STT, TTS, streaming text-to-TTS, and fake duplex primitives

## Recommended Reading With This Doc

For runtime structure:
- `runtime-overview.md`

For package ownership:
- `codebase-map.md`

For public surfaces and extension points:
- `api-and-runtime-surfaces.md`
