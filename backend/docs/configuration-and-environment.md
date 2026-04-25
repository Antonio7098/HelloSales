# Configuration And Environment

## Purpose
This document explains how backend runtime configuration works today.

It describes:
- how settings are loaded
- which settings matter most operationally
- how provider configuration is resolved
- how auth configuration is resolved
- how observability is configured
- which startup checks enforce configuration correctness

## Settings Model

The backend settings live in:
- `src/hello_sales_backend/platform/config/settings.py`

The runtime uses a `pydantic-settings` `BaseSettings` model.

Important characteristics:
- `HELLO_SALES_` is the settings prefix for most application settings
- `.env` is loaded by default
- extra environment variables are ignored
- string-like settings are aggressively stripped to avoid hidden whitespace bugs
- provider and observability variables use the same prefix

The cached accessor is:
- `get_settings()`

## Core Runtime Settings

High-signal settings include:
- `HELLO_SALES_APP_NAME`
- `HELLO_SALES_APP_VERSION`
- `HELLO_SALES_ENVIRONMENT`
- `HELLO_SALES_API_PREFIX`
- `HELLO_SALES_LOG_LEVEL`
- `HELLO_SALES_DATABASE_URL`
- `HELLO_SALES_CORS_ALLOWED_ORIGINS`
- `HELLO_SALES_STAGEFLOW_REQUIRED`
- `HELLO_SALES_STAGEFLOW_EVENT_QUEUE_SIZE`
- `HELLO_SALES_AUTH_PROVIDER`
- `HELLO_SALES_AUTH_REQUIRED`
- `HELLO_SALES_FRONTEND_APP_URL`

These shape the app identity, routing prefix, logging, database connection, workflow expectations, and API auth posture.

## Auth Configuration Model

The backend has an app-owned auth boundary in:
- `platform/auth/`
- `modules/auth/`

Relevant variables include:
- `HELLO_SALES_AUTH_PROVIDER`
- `HELLO_SALES_AUTH_REQUIRED`
- `HELLO_SALES_AUTH_SESSION_COOKIE_NAME`
- `HELLO_SALES_AUTH_SESSION_COOKIE_SECURE`
- `HELLO_SALES_AUTH_SESSION_COOKIE_DOMAIN`
- `HELLO_SALES_FRONTEND_APP_URL`
- `HELLO_SALES_WORKOS_API_KEY`
- `HELLO_SALES_WORKOS_CLIENT_ID`
- `HELLO_SALES_WORKOS_COOKIE_PASSWORD`
- `HELLO_SALES_WORKOS_REDIRECT_URI`
- `HELLO_SALES_WORKOS_BASE_URL`
- `HELLO_SALES_WORKOS_REQUEST_TIMEOUT_SECONDS`

Behavior:
- empty `HELLO_SALES_AUTH_PROVIDER` selects the no-op auth provider for local/test-only assembly
- `HELLO_SALES_AUTH_PROVIDER=workos` selects the WorkOS adapter
- `HELLO_SALES_AUTH_REQUIRED=true` requires a configured provider at startup
- the backend owns the sealed session cookie name, security attributes, and clear/set behavior
- `HELLO_SALES_FRONTEND_APP_URL` is used after successful auth callback redirects and logout return paths
- bearer tokens and session cookies both resolve through the provider-neutral auth port

The WorkOS adapter expects the provider to issue roles and permission claims. Backend routes authorize against permission slugs rather than binary `admin` / `user` checks, so provider-side role design can evolve without changing route code.

Current backend permission slugs include:
- `app.access`
- `sessions.read`
- `sessions.write`
- `sessions.read:any`
- `sessions.write:any`
- `company_profile.read`
- `company_profile.write`
- `jobs.read`
- `jobs.run`
- `workers.read`
- `workers.run`
- `workers.cancel`
- `system.read`
- `analytics.read`
- `web_search.use`
- `entity_operations.write`

## Observability Configuration Model

The backend now exposes environment-driven observability controls for metrics and tracing.

Relevant variables include:
- `HELLO_SALES_OBSERVABILITY_SERVICE_NAME`
- `HELLO_SALES_OBSERVABILITY_SERVICE_VERSION`
- `HELLO_SALES_OBSERVABILITY_METRICS_ENABLED`
- `HELLO_SALES_OBSERVABILITY_METRICS_EXPORTER`
- `HELLO_SALES_OBSERVABILITY_METRICS_ENDPOINT_ENABLED`
- `HELLO_SALES_OBSERVABILITY_METRICS_ENDPOINT_PATH`
- `HELLO_SALES_OBSERVABILITY_METRICS_HTTP_ENABLED`
- `HELLO_SALES_OBSERVABILITY_METRICS_HEALTH_ENABLED`
- `HELLO_SALES_OBSERVABILITY_METRICS_BACKGROUND_TASKS_ENABLED`
- `HELLO_SALES_OBSERVABILITY_METRICS_AGENTS_ENABLED`
- `HELLO_SALES_OBSERVABILITY_METRICS_WORKERS_ENABLED`
- `HELLO_SALES_OBSERVABILITY_TRACING_ENABLED`
- `HELLO_SALES_OBSERVABILITY_TRACING_EXPORTER`
- `HELLO_SALES_OBSERVABILITY_TRACING_OTLP_ENDPOINT`
- `HELLO_SALES_OBSERVABILITY_TRACING_OTLP_HEADERS`
- `HELLO_SALES_OBSERVABILITY_TRACING_OTLP_TIMEOUT_SECONDS`
- `HELLO_SALES_OBSERVABILITY_TRACING_HTTP_ENABLED`
- `HELLO_SALES_OBSERVABILITY_TRACING_BACKGROUND_TASKS_ENABLED`
- `HELLO_SALES_OBSERVABILITY_TRACING_AGENTS_ENABLED`
- `HELLO_SALES_OBSERVABILITY_TRACING_WORKERS_ENABLED`

Behavior:
- metrics and tracing can be enabled independently
- the operational metrics endpoint is disabled by default
- the metrics endpoint is mounted directly on the app rather than under `HELLO_SALES_API_PREFIX`
- tracing currently supports `console`, `otlp`, or disabled/no-op operation
- service metadata falls back to app metadata when observability-specific values are not set
- metric families can be disabled individually without removing the overall observability runtime
- agent metrics and tracing are controlled independently so generic-agent monitoring can be enabled without forcing those signals in every environment
- worker metrics and tracing are controlled independently so sprint-01 observability can be extended without forcing worker-specific signals on every environment

### OTLP Tracing Export

When `HELLO_SALES_OBSERVABILITY_TRACING_EXPORTER=otlp`, the backend exports spans to an OpenTelemetry Collector or other OTLP HTTP-compatible endpoint.

Relevant settings:
- `HELLO_SALES_OBSERVABILITY_TRACING_OTLP_ENDPOINT`
- `HELLO_SALES_OBSERVABILITY_TRACING_OTLP_HEADERS`
- `HELLO_SALES_OBSERVABILITY_TRACING_OTLP_TIMEOUT_SECONDS`

Behavior:
- the endpoint must start with `http://` or `https://`
- headers are parsed from a comma-separated `key=value` string
- OTLP export remains optional and disabled unless explicitly configured
- `console` and `none` remain valid low-friction modes for local development or tests

For the self-hosted stack introduced in Sprint 3, the intended endpoint is the OpenTelemetry Collector, typically `http://otel-collector:4318/v1/traces` inside the stack network or `http://localhost:4318/v1/traces` from local development.

## Provider Configuration Model

The backend currently resolves one shared LLM provider path that both the conversational agent runtime and the worker runtime consume.
It also resolves an optional public web-search provider path for the generic agent's `search_web` tool and the reusable `modules/web_search` service.
Voice primitives resolve separate STT, TTS, realtime voice, and turn-detection provider paths.

Relevant variables include:
- `HELLO_SALES_GENERIC_AGENT_PROVIDER`
- `HELLO_SALES_GENERIC_AGENT_MODEL`
- `HELLO_SALES_GENERIC_AGENT_BASE_URL`
- `HELLO_SALES_GENERIC_AGENT_TIMEOUT_SECONDS`
- `HELLO_SALES_GENERIC_AGENT_PROVIDER_MAX_RETRIES`
- `HELLO_SALES_GENERIC_AGENT_PROVIDER_RETRY_BACKOFF_SECONDS`
- `HELLO_SALES_GENERIC_AGENT_BACKUP_MODEL`
- `HELLO_SALES_GENERIC_AGENT_BACKUP_MODEL_ATTEMPT`
- `HELLO_SALES_AGENT_CONTEXT_PROFILE`
- `HELLO_SALES_GROQ_API_KEY`
- `HELLO_SALES_OPENROUTER_API_KEY`
- `HELLO_SALES_OPENAI_API_KEY`
- `HELLO_SALES_WEB_SEARCH_PROVIDER`
- `HELLO_SALES_WEB_SEARCH_API_KEY`
- `HELLO_SALES_TAVILY_API_KEY`
- `HELLO_SALES_WEB_SEARCH_TIMEOUT_SECONDS`
- `HELLO_SALES_WEB_SEARCH_DEFAULT_MAX_RESULTS`
- `HELLO_SALES_WEB_SEARCH_REQUIRED`
- `HELLO_SALES_WEB_SEARCH_REQUIRES_APPROVAL`
- `HELLO_SALES_VOICE_STT_PROVIDER`
- `HELLO_SALES_VOICE_TTS_PROVIDER`
- `HELLO_SALES_VOICE_REALTIME_PROVIDER`
- `HELLO_SALES_VOICE_TURN_DETECTION_PROVIDER`
- `HELLO_SALES_VOICE_TRANSPORT_PROVIDER`
- `HELLO_SALES_VOICE_REQUIRED`
- `HELLO_SALES_VOICE_STT_MODEL`
- `HELLO_SALES_VOICE_TTS_MODEL`
- `HELLO_SALES_VOICE_DEFAULT_TTS_VOICE`
- `HELLO_SALES_VOICE_MAX_AUDIO_BYTES`
- `HELLO_SALES_VOICE_PERSIST_RAW_AUDIO`

The settings name remains `generic_agent_*` because that path existed before the neutral `platform/llm/` extraction.
At runtime, the resolved provider now backs:
- conversational response generation in the agent runtime
- JSON generation and structured worker execution in the worker runtime

`HELLO_SALES_AGENT_CONTEXT_PROFILE` selects the runtime context profile used by the generic agent.
The default is `basic-session-v1`, which preserves completed session summary plus recent session item assembly.

### Provider Resolution
The settings model computes resolved values through properties:
- `resolved_generic_agent_provider`
- `resolved_generic_agent_model`
- `resolved_generic_agent_base_url`
- `resolved_generic_agent_api_key`

Built-in provider base URLs currently exist for:
- `groq`
- `openrouter`
- `openai`
- `openai-compatible`

Resolution behavior is:
- explicit custom base URL wins when provided
- otherwise known providers get their default base URL
- API key is chosen based on the resolved provider name
- retryable provider transport failures are retried up to `HELLO_SALES_GENERIC_AGENT_PROVIDER_MAX_RETRIES`
- retry backoff is linear and controlled by `HELLO_SALES_GENERIC_AGENT_PROVIDER_RETRY_BACKOFF_SECONDS`
- when configured, `HELLO_SALES_GENERIC_AGENT_BACKUP_MODEL` is selected starting at `HELLO_SALES_GENERIC_AGENT_BACKUP_MODEL_ATTEMPT`

### Public Web Search Provider Resolution

The web-search provider is intentionally separate from the LLM provider.
The current built-in adapter is:
- `tavily`

Resolution behavior:
- `HELLO_SALES_WEB_SEARCH_PROVIDER=tavily` selects the Tavily adapter
- `HELLO_SALES_WEB_SEARCH_API_KEY` is the generic web-search key override
- `HELLO_SALES_TAVILY_API_KEY` is used when the provider is `tavily` and no generic web-search key is set
- no provider or missing credentials resolves to the no-op provider unless web search is required
- `HELLO_SALES_WEB_SEARCH_REQUIRES_APPROVAL=true` makes `search_web` pause for approval before sending a query to the provider

Readiness behavior:
- web search is optional by default and appears as disabled or degraded in readiness/diagnostics when not configured
- `HELLO_SALES_WEB_SEARCH_REQUIRED=true` makes readiness fail if a provider is selected without usable credentials
- diagnostics expose provider `kind=web_search`, availability, required state, and degraded state

### Voice Provider Resolution

The current built-in voice adapter is deterministic fake-only:
- `fake`

Resolution behavior:
- `HELLO_SALES_VOICE_STT_PROVIDER=fake` selects `fake-stt`
- `HELLO_SALES_VOICE_TTS_PROVIDER=fake` selects `fake-tts`
- `HELLO_SALES_VOICE_REALTIME_PROVIDER=fake` selects `fake-realtime-voice`
- `HELLO_SALES_VOICE_TURN_DETECTION_PROVIDER=fake` selects `fake-turn-detection`
- empty provider settings resolve to disabled providers
- `HELLO_SALES_VOICE_REQUIRED=true` makes readiness fail unless STT, TTS, and turn detection are configured

Raw audio persistence remains disabled unless `HELLO_SALES_VOICE_PERSIST_RAW_AUDIO=true`.
The default maximum audio payload is 25 MB through `HELLO_SALES_VOICE_MAX_AUDIO_BYTES`.

## Startup Validation

Startup validation lives in:
- `src/hello_sales_backend/platform/composition/startup.py`

Current startup validation checks:
- environment must be one of `development`, `test`, `staging`, `production`
- auth provider must be supported
- auth-required deployments must configure a provider
- WorkOS configuration must be complete when WorkOS is selected
- configured generic-agent provider must be supported
- provider config must not be partial
- required web-search readiness fails when the selected search provider has no usable credentials

### Partial Provider Config
The backend treats partial provider configuration as a startup error.

Examples of invalid shapes:
- auth required without `HELLO_SALES_AUTH_PROVIDER`
- `HELLO_SALES_AUTH_PROVIDER=workos` without API key, client id, cookie password, or redirect URI
- provider/model/base-url hints without a usable API key
- API key present but model/base-url shape incomplete when required

This is intentionally strict so provider-backed behavior does not fail later in confusing runtime paths.

## Database Configuration Behavior

The key database setting is:
- `HELLO_SALES_DATABASE_URL`

Current runtime behavior:
- development and production are Postgres-first by default
- tests often use SQLite for fast local execution
- readiness behavior changes depending on whether the configured DB is SQLite or not

The app container also uses the DB scheme to choose some runtime behavior, such as whether to use the in-memory agent store or the SQLAlchemy-backed agent store.
Worker runs currently use an in-memory worker store in all environments, which is intentional scaffold-stage behavior rather than durable SQL persistence.

## Workflow Configuration Behavior

The main workflow setting is:
- `HELLO_SALES_STAGEFLOW_REQUIRED`

Behavior:
- if Stageflow is required and not installed, startup/runtime behavior should fail loudly
- if Stageflow is optional and not installed, the system can degrade rather than fail everywhere

This is reflected in both startup/runtime assembly and readiness behavior.

## Environment Philosophy

The current backend tries to follow a few rules:
- configuration should be explicit
- hidden whitespace and malformed values should be normalized early
- provider-backed paths should fail early on invalid configuration
- environment should influence behavior predictably rather than through ad hoc flags

## Typical Local Development Shape

Common local development shape:
- Postgres database URL
- `HELLO_SALES_ENVIRONMENT=development`
- optional `.env` file
- observability metrics and tracing disabled until explicitly needed
- `HELLO_SALES_OBSERVABILITY_METRICS_ENDPOINT_ENABLED=true` only when an operator or developer wants the operational metrics surface
- provider settings present when running real-provider smoke suites
- provider settings omitted when running deterministic local scaffold paths

## Where To Read In Code

High-signal files:
- `platform/config/settings.py`
- `platform/composition/startup.py`
- `platform/composition/providers.py`
- `app.py`
- `backend/.env.example`
