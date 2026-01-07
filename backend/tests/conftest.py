"""Test configuration for enterprise backend - WorkOS only."""

import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.database as database_module
from app.ai.substrate.events import wait_for_event_sink_tasks
from app.main import app

os.environ["ENVIRONMENT"] = "development"


@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the entire test session to avoid cross-loop issues."""

    loop = asyncio.new_event_loop()
    yield loop
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()


# Test database URL (use the dev Postgres container exposed on localhost:5433).
# This matches docker-compose.yml: "5433:5432".
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://eloquence:eloquence_dev@localhost:5433/eloquence_enterprise_test",
)

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_ALEMBIC_INI = _BACKEND_ROOT / "alembic.ini"


async def _ensure_test_database_exists() -> None:
    url = make_url(TEST_DATABASE_URL)
    if not url.database:
        raise RuntimeError("TEST_DATABASE_URL is missing a database name")
    db_name = url.database

    admin_url = url.set(database="postgres")
    admin_dsn = admin_url.render_as_string(hide_password=False).replace(
        "postgresql+asyncpg://",
        "postgresql://",
    )

    try:
        conn = await asyncpg.connect(dsn=admin_dsn)
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Unable to connect to the test Postgres instance.\n"
            f"Attempted DSN: {admin_url.render_as_string(hide_password=True)}\n\n"
            "Make sure the repo infrastructure is running:\n"
            "  - make dev\n"
            "or\n"
            "  - docker-compose up -d postgres redis\n"
            "\nExpected Postgres port: localhost:5433\n"
        ) from exc
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()


async def _reset_test_database_schema() -> None:
    url = make_url(TEST_DATABASE_URL)
    dsn = url.render_as_string(hide_password=False).replace(
        "postgresql+asyncpg://",
        "postgresql://",
    )

    try:
        conn = await asyncpg.connect(dsn=dsn)
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Unable to connect to the test database to reset schema.\n"
            f"Attempted DSN: {url.render_as_string(hide_password=True)}\n\n"
            "Make sure the repo infrastructure is running:\n"
            "  - make dev\n"
            "or\n"
            "  - docker-compose up -d postgres redis\n"
            "\nExpected Postgres port: localhost:5433\n"
        ) from exc
    try:
        await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        await conn.execute("CREATE SCHEMA public")
    finally:
        await conn.close()


# Flag to track if we're running unit tests that don't need DB
_SKIP_DB_FOR_UNIT_TESTS = False


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest to skip DB for pure unit tests."""
    global _SKIP_DB_FOR_UNIT_TESTS

    # Check if we're running only unit tests in ai/substrate
    if config.getoption("collectonly"):
        return

    # Check for specific test paths
    args = [arg for arg in config.args if "unit" in arg or "test_pipeline_factory" in arg]
    if args:
        _SKIP_DB_FOR_UNIT_TESTS = True


def _should_skip_migrations() -> bool:
    """Check if we should skip database migrations for this test."""
    return _SKIP_DB_FOR_UNIT_TESTS


def _is_unit_test_without_db() -> bool:
    """Check if this is a unit test that doesn't need database access."""
    return _SKIP_DB_FOR_UNIT_TESTS


@pytest.fixture(scope="session")
def apply_test_migrations() -> None:
    # Skip migrations for pure unit tests
    if _should_skip_migrations():
        return None

    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

    asyncio.run(_ensure_test_database_exists())
    asyncio.run(_reset_test_database_schema())

    env = os.environ.copy()
    env["DATABASE_URL"] = TEST_DATABASE_URL
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(_ALEMBIC_INI),
            "upgrade",
            "head",
        ],
        cwd=str(_BACKEND_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Alembic migrations failed for test database.\n"
            f"stdout:\n{result.stdout}\n\n"
            f"stderr:\n{result.stderr}"
        )


@pytest.fixture(scope="session", autouse=True)
def _ensure_test_schema_ready(apply_test_migrations) -> None:
    # Skip if migrations were skipped
    if _should_skip_migrations():
        return None
    _ = apply_test_migrations


@pytest_asyncio.fixture(autouse=True)
async def reset_database_globals():
    """Flush event-sink tasks and dispose DB globals before/after each test."""
    if _is_unit_test_without_db():
        yield
        return

    async def _flush_and_dispose() -> None:
        await wait_for_event_sink_tasks()

        dispose_fn = getattr(database_module, "dispose_async_engine", None)
        if dispose_fn is not None:
            await dispose_fn()

        reset_fn = getattr(database_module, "reset_async_session_factory", None)
        if reset_fn is not None:
            reset_fn()

    await _flush_and_dispose()

    yield

    await _flush_and_dispose()


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Clear cached settings before each test so env vars are re-read."""
    from app.config import get_settings

    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["ENVIRONMENT"] = "development"
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def reset_websocket_manager():
    """Reset global WebSocket manager between tests to prevent interference."""
    from app.api.ws.manager import _manager

    # Reset the global connection manager
    original_manager = _manager
    import app.api.ws.manager as ws_manager_module

    ws_manager_module._manager = None
    yield
    # Restore original state if needed
    ws_manager_module._manager = original_manager


@pytest.fixture(autouse=True)
def reset_auth_singletons():
    """Reset global auth singletons between tests to prevent interference."""
    from app.auth.workos import _workos_jwks_client

    # Reset auth singletons
    original_workos_jwks = _workos_jwks_client

    import app.auth.workos as workos_module

    workos_module._workos_jwks_client = None

    yield

    # Restore original state if needed
    workos_module._workos_jwks_client = original_workos_jwks


@pytest.fixture(autouse=True)
def reset_provider_singletons():
    """Reset global provider singletons between tests to prevent interference."""
    try:
        from app.ai.providers.factory import (
            get_llm_provider,
            get_stt_provider,
            get_tts_provider,
        )

        # Clear the lru_cache for providers
        get_llm_provider.cache_clear()
        get_stt_provider.cache_clear()
        get_tts_provider.cache_clear()

        yield

        # Clear again after test
        get_llm_provider.cache_clear()
        get_stt_provider.cache_clear()
        get_tts_provider.cache_clear()
    except ImportError:
        # If provider functions don't exist, just yield
        yield


@pytest.fixture(autouse=True)
def reset_environment_state():
    """Reset environment variables between tests to prevent interference."""
    import os

    # Store original environment state
    original_env: dict[str, str | None] = {}
    test_specific_vars = [
        "ENVIRONMENT",
        "GROQ_API_KEY",
        "LLM_PROVIDER",
        "STT_PROVIDER",
        "TTS_PROVIDER",
        "DATABASE_URL",
        "TEST_DATABASE_URL",
        "STUB_LLM_FORCE_STREAM_TEXT",
        "STUB_LLM_STREAM_MODE",
        "STUB_LLM_STREAM_TEXT",
        "STUB_LLM_STREAM_CHUNK_SIZE",
        "STUB_LLM_STREAM_DELAY_MS",
        "STUB_LLM_FAIL_AFTER_CHUNKS",
        "POLICY_FORCE_CHECKPOINT",
        "POLICY_FORCE_DECISION",
        "POLICY_FORCE_REASON",
        "GUARDRAILS_FORCE_CHECKPOINT",
        "GUARDRAILS_FORCE_DECISION",
        "GUARDRAILS_FORCE_REASON",
        "WORKOS_CLIENT_ID",
        "WORKOS_API_KEY",
        "CONTEXT_ENRICHER_PROFILE_ENABLED",
    ]

    for var in test_specific_vars:
        original_env[var] = os.environ.get(var)

    # Set clean baseline and clear leftover overrides
    baseline = {
        "DATABASE_URL": TEST_DATABASE_URL,
        "ENVIRONMENT": "development",
        "DATABASE_DISABLE_POOLING": "true",
        "LLM_PROVIDER": "stub",
        "STT_PROVIDER": "stub",
        "TTS_PROVIDER": "stub",
        "WORKOS_CLIENT_ID": "test_client_id",
        "WORKOS_API_KEY": "test_api_key",
    }

    for var in test_specific_vars:
        if var not in baseline:
            os.environ.pop(var, None)

    for key, value in baseline.items():
        os.environ[key] = value

    yield

    # Restore original environment
    for var, value in original_env.items():
        if value is None:
            os.environ.pop(var, None)
        else:
            os.environ[var] = value


@pytest.fixture(autouse=True)
def cleanup_database_data():
    """Clean up database data between tests to prevent interference."""
    import asyncpg
    from sqlalchemy.engine.url import make_url

    # Only clean up for integration tests
    test_name = ""
    if hasattr(pytest, "current_test_node"):
        test_name = str(pytest.current_test_node) if hasattr(pytest, "current_test_node") else ""
    if "integration" not in test_name:
        yield
        return

    url = make_url(TEST_DATABASE_URL)
    dsn = url.render_as_string(hide_password=False).replace(
        "postgresql+asyncpg://",
        "postgresql://",
    )

    async def _cleanup():
        try:
            conn = await asyncpg.connect(dsn=dsn)
            try:
                # Clean up all test data but preserve schema
                await conn.execute(
                    "DELETE FROM pipeline_events WHERE created_at > NOW() - INTERVAL '1 hour'"
                )
                await conn.execute(
                    "DELETE FROM pipeline_runs WHERE created_at > NOW() - INTERVAL '1 hour'"
                )
                await conn.execute(
                    "DELETE FROM interactions WHERE created_at > NOW() - INTERVAL '1 hour'"
                )
                await conn.execute(
                    "DELETE FROM messages WHERE created_at > NOW() - INTERVAL '1 hour'"
                )
                await conn.execute("DELETE FROM users WHERE created_at > NOW() - INTERVAL '1 hour'")
                await conn.execute(
                    "DELETE FROM organizations WHERE created_at > NOW() - INTERVAL '1 hour'"
                )
                await conn.execute(
                    "DELETE FROM organization_memberships WHERE created_at > NOW() - INTERVAL '1 hour'"
                )
            finally:
                await conn.close()
        except Exception as e:
            # Log but don't fail the test if cleanup fails
            print(f"WARNING: Database cleanup failed: {e}")

    # Run cleanup before test
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, create a task
            task = loop.create_task(_cleanup())
            # Wait for it to complete with timeout
            loop.run_until_complete(asyncio.wait_for(task, timeout=5.0))
        else:
            # If loop is not running, run it
            loop.run_until_complete(_cleanup())
    except Exception as e:
        print(f"WARNING: Pre-test cleanup failed: {e}")

    yield

    # Run cleanup after test
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = loop.create_task(_cleanup())
            loop.run_until_complete(asyncio.wait_for(task, timeout=5.0))
        else:
            loop.run_until_complete(_cleanup())
    except Exception as e:
        print(f"WARNING: Post-test cleanup failed: {e}")


@pytest_asyncio.fixture
async def test_engine(apply_test_migrations):
    """Create test database engine.

    Note: We no longer drop tables after tests. The schema is managed by
    Alembic migrations, and dropping tables mid-suite breaks subsequent tests.
    Use `alembic upgrade head` before running tests to ensure schema exists.
    """
    _ = apply_test_migrations
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def client(apply_test_migrations) -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    _ = apply_test_migrations
    with TestClient(app) as c:
        yield c


@pytest_asyncio.fixture
async def async_client(apply_test_migrations) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    _ = apply_test_migrations
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def mock_workos_token() -> str:
    """Create a mock WorkOS JWT token for testing (dev mode)."""
    # In development mode, "dev_token" is accepted
    return "dev_token"


@pytest.fixture
def mock_workos_claims() -> dict:
    """Mock WorkOS claims for testing."""
    return {
        "sub": "workos_user_123",
        "email": "workos@example.com",
        "org_id": "org_enterprise_123",
    }
