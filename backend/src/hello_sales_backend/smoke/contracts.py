"""Core contracts for executable smoke suites."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from alembic.config import Config
from pydantic import BaseModel

from alembic import command
from hello_sales_backend.app import create_app
from hello_sales_backend.platform.auth.contracts import AuthProviderPort, AuthResult
from hello_sales_backend.platform.composition.overrides import AppOverrides
from hello_sales_backend.platform.config.settings import Settings, get_settings
from hello_sales_backend.platform.db.engine import build_engine
from hello_sales_backend.platform.db.models import Base
from hello_sales_backend.shared.auth import (
    ANALYTICS_READ_PERMISSION,
    APP_ACCESS_PERMISSION,
    COMPANY_PROFILE_READ_PERMISSION,
    COMPANY_PROFILE_WRITE_PERMISSION,
    ENTITY_OPERATIONS_WRITE_PERMISSION,
    JOBS_READ_PERMISSION,
    JOBS_RUN_PERMISSION,
    SESSIONS_READ_PERMISSION,
    SESSIONS_WRITE_PERMISSION,
    SYSTEM_READ_PERMISSION,
    WEB_SEARCH_USE_PERMISSION,
    WORKERS_CANCEL_PERMISSION,
    WORKERS_READ_PERMISSION,
    WORKERS_RUN_PERMISSION,
    AuthContext,
)


class SmokeAuthProvider(AuthProviderPort):
    """Local-only auth provider for CLI smoke suites."""

    provider_name = "smoke"

    def is_configured(self) -> bool:
        return True

    def get_authorization_url(self, *, state: str | None = None) -> str:
        del state
        return ""

    async def exchange_code(self, *, code: str) -> AuthResult:
        del code
        return await self.authenticate(session_token=None)

    async def authenticate(
        self,
        *,
        session_token: str | None,
        bearer_token: str | None = None,
    ) -> AuthResult:
        del session_token, bearer_token
        return AuthResult(
            context=AuthContext(
                provider_name=self.provider_name,
                actor_id="smoke-actor",
                user_id="smoke-user",
                org_id="smoke-org",
                email="smoke@example.test",
                permissions=(
                    APP_ACCESS_PERMISSION,
                    SESSIONS_READ_PERMISSION,
                    SESSIONS_WRITE_PERMISSION,
                    SYSTEM_READ_PERMISSION,
                    JOBS_READ_PERMISSION,
                    JOBS_RUN_PERMISSION,
                    ANALYTICS_READ_PERMISSION,
                    WEB_SEARCH_USE_PERMISSION,
                    ENTITY_OPERATIONS_WRITE_PERMISSION,
                    COMPANY_PROFILE_READ_PERMISSION,
                    COMPANY_PROFILE_WRITE_PERMISSION,
                    WORKERS_READ_PERMISSION,
                    WORKERS_RUN_PERMISSION,
                    WORKERS_CANCEL_PERMISSION,
                ),
            ),
            source=self.provider_name,
        )

    async def get_logout_url(self, *, session_token: str | None) -> str | None:
        del session_token
        return None

    async def aclose(self) -> None:
        return None


@dataclass(frozen=True, slots=True)
class SmokeContext:
    """Runtime context shared by smoke suites."""

    settings: Settings
    overrides: AppOverrides | None = None

    @classmethod
    def create(
        cls,
        *,
        settings: Settings | None = None,
        overrides: AppOverrides | None = None,
    ) -> SmokeContext:
        resolved_settings = settings or get_settings()
        resolved_overrides = overrides
        if not resolved_settings.auth_required and (
            resolved_overrides is None or resolved_overrides.auth_provider is None
        ):
            resolved_overrides = resolved_overrides or AppOverrides()
            resolved_overrides.auth_provider = SmokeAuthProvider()
        return cls(settings=resolved_settings, overrides=resolved_overrides)

    def build_app(self) -> Any:
        """Build an application instance for the smoke run."""

        return create_app(self.settings, overrides=self.overrides)

    async def prepare_runtime(self) -> None:
        """Prepare runtime dependencies required by smoke execution."""

        if self.settings.database_url.startswith("sqlite+"):
            return
        alembic_ini = Path(__file__).resolve().parents[3] / "alembic.ini"
        config = Config(str(alembic_ini))
        config.set_main_option("sqlalchemy.url", self.settings.database_url)
        await asyncio.to_thread(command.upgrade, config, "head")
        engine = build_engine(self.settings)
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
        finally:
            await engine.dispose()


class SmokeDefinition(BaseModel):
    """Serializable smoke metadata."""

    name: str
    description: str


class SmokeExecutionResult(BaseModel):
    """Serialized smoke execution output."""

    smoke_name: str
    description: str
    payload: dict[str, object]

    @classmethod
    def from_result(cls, smoke: SmokeCase, result: BaseModel) -> SmokeExecutionResult:
        return cls(
            smoke_name=smoke.name,
            description=smoke.description,
            payload=result.model_dump(mode="json"),
        )


class SmokeCase(ABC):
    """Base contract for concrete smoke suites."""

    name: str
    description: str

    @abstractmethod
    async def run(self, context: SmokeContext) -> BaseModel:
        """Execute the smoke suite."""
