# Application Blueprint

## Purpose
This blueprint defines the preferred foundation for the next backend project.

It is intentionally biased toward:
- FastAPI
- async SQLAlchemy
- Stageflow orchestration
- strong module boundaries
- explicit composition
- testable provider seams
- observable background execution

This document is implementation-oriented.
For normative rules, use [ARCHITECTURE_RULES.md](/home/antonioborgerees/coding/HelloSales/ops/ARCHITECTURE_RULES.md).

## Foundation Goals

The foundation must make these things easy:
- adding new bounded-context modules
- swapping AI providers
- adding workflows without leaking orchestration everywhere
- testing business logic without real DB or real providers
- tracing requests, tasks, and provider calls
- handling background failures without silent data loss

The foundation must make these things hard:
- importing module internals across boundaries
- doing blocking DB work in async handlers
- reaching into container internals from routes
- patching private fields in tests
- hiding provider and workflow failures

## Recommended Backend Shape

```text
backend/
├── pyproject.toml
├── alembic.ini
├── alembic/
├── src/
│   └── {package}/
│       ├── __init__.py
│       ├── app.py
│       ├── modules/
│       │   └── {module}/
│       │       ├── __init__.py
│       │       ├── bootstrap.py
│       │       ├── domain/
│       │       ├── use_cases/
│       │       ├── workflows/
│       │       ├── infra/
│       │       └── models.py
│       ├── entrypoints/
│       │   └── http/
│       │       ├── __init__.py
│       │       ├── router.py
│       │       ├── dependencies.py
│       │       ├── error_handlers.py
│       │       ├── schemas.py
│       │       └── routes/
│       ├── platform/
│       │   ├── composition/
│       │   │   ├── app_container.py
│       │   │   ├── module_registry.py
│       │   │   ├── providers.py
│       │   │   └── startup.py
│       │   ├── config/
│       │   │   └── settings.py
│       │   ├── db/
│       │   │   ├── base.py
│       │   │   ├── engine.py
│       │   │   ├── session.py
│       │   │   ├── uow.py
│       │   │   └── migrations.py
│       │   ├── observability/
│       │   │   ├── logging.py
│       │   │   ├── middleware.py
│       │   │   ├── tracing.py
│       │   │   └── events.py
│       │   ├── providers/
│       │   │   └── llm/
│       │   ├── tasks/
│       │   │   ├── runner.py
│       │   │   └── models.py
│       │   └── workflows/
│       │       ├── runtime.py
│       │       ├── executor.py
│       │       └── registry.py
│       └── shared/
│           ├── errors.py
│           ├── ids.py
│           ├── types.py
│           └── protocols.py
└── tests/
    ├── unit/
    ├── integration/
    ├── smoke/
    └── conftest.py
```

## Runtime Model

### Request Flow

Preferred request flow:

```text
FastAPI route
-> dependency helper
-> module facade/service
-> use case
-> ports
-> infra implementations
-> database / provider / broker
```

Routes should not:
- create sessions
- call provider SDKs
- reach into the container directly
- coordinate multiple unrelated services inline

### Workflow Flow

Preferred orchestration flow:

```text
module workflow service
-> app-owned workflow facade
-> Stageflow runtime wrapper
-> provider + persistence adapters
-> telemetry/event sink
```

Modules may use Stageflow concepts inside the orchestration boundary, but the rest of the system should depend on app-owned helpers instead of raw engine details.

## Async and Persistence Standard

Use async SQLAlchemy from day one.

Preferred setup:
- `AsyncEngine`
- `async_sessionmaker`
- explicit unit of work or transaction boundary
- one repository implementation per port

Avoid:
- sync session objects in async services
- direct session usage in routes
- passing sessions through unrelated layers

Recommended direction:

```python
class UnitOfWork(Protocol):
    users: UserRepository
    practice_runs: PracticeRunRepository

    async def __aenter__(self) -> "UnitOfWork": ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
```

Not every module needs a large unit-of-work abstraction on day one, but session ownership must still be explicit.

## Composition Model

### App Container

The app container should hold lifecycle resources and module bundles, not module internals.

Preferred shape:

```python
@dataclass(slots=True)
class AppContainer:
    settings: Settings
    db: DatabaseRuntime
    observability: ObservabilityRuntime
    tasks: TaskRunner
    workflows: WorkflowRuntime
    modules: ModuleRegistry
```

### Module Bundle

Each module owns its own bootstrap and returns a typed bundle.

Example:

```python
@dataclass(slots=True)
class PracticeModule:
    service: PracticeService
    routes: PracticeRouteDependencies
```

The top-level composition layer should call:

```python
practice_module = build_practice_module(shared_runtime)
assistant_module = build_assistant_module(shared_runtime, practice_module=practice_module)
```

This keeps composition centralized without making one file know every internal detail.

## Module Template

Each new module should start with this shape:

```text
modules/{module}/
├── __init__.py
├── bootstrap.py
├── domain/
│   ├── __init__.py
│   ├── entities.py
│   ├── value_objects.py
│   └── exceptions.py
├── use_cases/
│   ├── __init__.py
│   ├── commands.py
│   ├── views.py
│   ├── ports.py
│   └── {module}_service.py
├── workflows/
│   └── {workflow}.py
├── infra/
│   ├── persistence.py
│   ├── queries.py
│   ├── providers.py
│   └── realtime.py
└── models.py
```

### Module Bootstrap Pattern

Example:

```python
@dataclass(slots=True)
class PracticeModule:
    service: PracticeService


def build_practice_module(deps: SharedModuleDeps) -> PracticeModule:
    repository = SqlAlchemyPracticeRepository(deps.session_factory)
    marker = build_assessment_marker(deps.providers.llm, deps.observability)
    service = PracticeService(
        repository=repository,
        assessment_marker=marker,
        workflow_runtime=deps.workflows,
    )
    return PracticeModule(service=service)
```

This is the correct place to assemble concrete infra for one bounded context.

## Ports and Adapters

### Define Ports in Use Cases

Example:

```python
class ChatModelPort(Protocol):
    async def generate(self, prompt: PromptEnvelope) -> ChatResult: ...


class PracticeRepository(Protocol):
    async def get_run(self, run_id: str) -> PracticeRun | None: ...
    async def save_run(self, run: PracticeRun) -> None: ...
```

### Implement in Infra or Platform Providers

Example:

```python
class OpenRouterChatModel(ChatModelPort):
    ...


class SqlAlchemyPracticeRepository(PracticeRepository):
    ...
```

### Keep DTO Boundaries Explicit

Use:
- `commands.py` for app inputs
- `views.py` for app outputs
- domain entities for internal business behavior

Do not return ORM records or vendor payloads from services.

## Stageflow Integration Pattern

Stageflow should be wrapped behind app-owned runtime helpers.

Recommended files:
- `platform/workflows/runtime.py`
- `platform/workflows/registry.py`
- `platform/workflows/executor.py`

Responsibilities:
- Stageflow import and initialization
- interceptor setup
- event sink wiring
- trace correlation
- execution metadata
- cancellation support

Modules should consume a small facade such as:

```python
class WorkflowRuntime(Protocol):
    async def run(self, definition: WorkflowDefinition, context: WorkflowContext) -> WorkflowResult: ...
```

This gives you an exit path if orchestration needs change later.

## Background Task Strategy

Background tasks need stronger structure than raw `create_task`.

Preferred shape:

```python
@dataclass(slots=True)
class TaskMetadata:
    task_id: str
    purpose: str
    request_id: str | None
    trace_id: str | None
    actor_id: str | None


class TaskRunner(Protocol):
    def start(self, metadata: TaskMetadata, coro: Coroutine[Any, Any, Any]) -> None: ...
    async def shutdown(self) -> None: ...
```

Required behavior:
- record failures
- attach correlation metadata
- cancel on shutdown
- expose failures for logging and health checks

## Observability Blueprint

Set this up early:
- structured logging
- request id and trace id middleware
- provider call telemetry
- workflow event sink
- startup and shutdown logging
- health endpoints for liveness and readiness

Recommended minimum event types:
- request started
- request failed
- workflow started
- workflow completed
- workflow failed
- provider call started
- provider call completed
- provider call failed
- background task failed

## Testing Blueprint

### Unit Tests
Target:
- domain rules
- use-case behavior
- workflow branching logic with fake ports

### Integration Tests
Target:
- DB mappings
- module bootstrap wiring
- transaction behavior
- provider adapters against test doubles

### Smoke Tests
Target:
- app startup
- migrations
- critical route registration
- orchestration runtime boot
- one provider path

### Test Override Pattern

Avoid patching private attributes.

Preferred:
- override provider factories in bootstrap
- inject fake ports into module builders
- provide a test container builder

Example:

```python
test_container = build_app_container(
    settings=test_settings,
    overrides=AppOverrides(
        llm_provider=FakeLLMProvider(...),
        task_runner=InlineTaskRunner(),
    ),
)
```

## What Is Safe To Build Before The Brief

Build now:
- package layout
- app factory
- config/settings
- async DB engine and session factory
- alembic wiring
- task runner
- workflow runtime wrapper
- logging and tracing middleware
- error model and error handlers
- health endpoints
- composition package
- one sample module shell with ports and bootstrap
- test harness

Wait for the brief before building:
- real bounded contexts
- real database schema beyond operational core
- product-specific workflows
- prompt structures
- auth and tenancy details unless already known
- public API surface beyond health and internal diagnostics

## Suggested First Build Order

1. `pyproject.toml` with FastAPI, async SQLAlchemy, Alembic, Stageflow, HTTP client, observability, tests, Ruff, and mypy
2. `settings.py`
3. `platform/db/engine.py`, `session.py`, `base.py`
4. Alembic init and metadata wiring
5. `platform/observability/`
6. `platform/tasks/runner.py`
7. `platform/workflows/runtime.py`
8. `platform/composition/`
9. `app.py`
10. `entrypoints/http/` with `router.py`, `dependencies.py`, `error_handlers.py`, and `/health`
11. one empty sample module with `bootstrap.py`
12. unit, integration, and smoke test scaffolding

## Anti-Patterns To Avoid

Do not carry these into the next project:
- sync SQLAlchemy sessions inside async request handlers
- one giant container with every concrete dependency hard-coded
- routes using `app.state.container` as a service locator
- services importing ORM records directly from platform DB packages
- module root exports that leak infra implementations
- tests that replace private service fields
- background task errors that are merely collected and forgotten

## Final Standard

The foundation is good when:
- module growth does not increase coupling linearly
- provider changes stay local to adapters and bootstrap wiring
- workflows are observable and cancellable
- tests replace collaborators through public seams
- routes remain thin even as features grow
- the composition root stays readable after many modules are added
