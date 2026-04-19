# Configuration And Environment

## Purpose
This document explains how backend runtime configuration works today.

It describes:
- how settings are loaded
- which settings matter most operationally
- how provider configuration is resolved
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

These shape the app identity, routing prefix, logging, database connection, and workflow expectations.

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
- `HELLO_SALES_OBSERVABILITY_TRACING_HTTP_ENABLED`
- `HELLO_SALES_OBSERVABILITY_TRACING_BACKGROUND_TASKS_ENABLED`
- `HELLO_SALES_OBSERVABILITY_TRACING_AGENTS_ENABLED`
- `HELLO_SALES_OBSERVABILITY_TRACING_WORKERS_ENABLED`

Behavior:
- metrics and tracing can be enabled independently
- the operational metrics endpoint is disabled by default
- the metrics endpoint is mounted directly on the app rather than under `HELLO_SALES_API_PREFIX`
- tracing currently supports `console` export or disabled/no-op operation
- service metadata falls back to app metadata when observability-specific values are not set
- metric families can be disabled individually without removing the overall observability runtime
- agent metrics and tracing are controlled independently so generic-agent monitoring can be enabled without forcing those signals in every environment
- worker metrics and tracing are controlled independently so sprint-01 observability can be extended without forcing worker-specific signals on every environment

## Provider Configuration Model

The backend currently resolves one shared LLM provider path that both the conversational agent runtime and the worker runtime consume.

Relevant variables include:
- `HELLO_SALES_GENERIC_AGENT_PROVIDER`
- `HELLO_SALES_GENERIC_AGENT_MODEL`
- `HELLO_SALES_GENERIC_AGENT_BASE_URL`
- `HELLO_SALES_GENERIC_AGENT_TIMEOUT_SECONDS`
- `HELLO_SALES_GROQ_API_KEY`
- `HELLO_SALES_OPENROUTER_API_KEY`
- `HELLO_SALES_OPENAI_API_KEY`

The settings name remains `generic_agent_*` because that path existed before the neutral `platform/llm/` extraction.
At runtime, the resolved provider now backs:
- conversational response generation in the agent runtime
- JSON generation and structured worker execution in the worker runtime

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

## Startup Validation

Startup validation lives in:
- `src/hello_sales_backend/platform/composition/startup.py`

Current startup validation checks:
- environment must be one of `development`, `test`, `staging`, `production`
- configured generic-agent provider must be supported
- provider config must not be partial

### Partial Provider Config
The backend treats partial provider configuration as a startup error.

Examples of invalid shapes:
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
