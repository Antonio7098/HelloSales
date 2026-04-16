# Configuration And Environment

## Purpose
This document explains how backend runtime configuration works today.

It describes:
- how settings are loaded
- which settings matter most operationally
- how provider configuration is resolved
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

## Provider Configuration Model

The backend currently supports a generic-agent provider path.

Relevant variables include:
- `GENERIC_AGENT_PROVIDER`
- `GENERIC_AGENT_MODEL`
- `GENERIC_AGENT_BASE_URL`
- `GENERIC_AGENT_TIMEOUT_SECONDS`
- `GROQ_API_KEY`
- `OPENROUTER_API_KEY`
- `OPENAI_API_KEY`

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
- provider settings present when running real-provider smoke suites
- provider settings omitted when running deterministic local scaffold paths

## Where To Read In Code

High-signal files:
- `platform/config/settings.py`
- `platform/composition/startup.py`
- `platform/composition/providers.py`
- `app.py`
- `backend/.env.example`
