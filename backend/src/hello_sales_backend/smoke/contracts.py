"""Core contracts for executable smoke suites."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from pydantic import BaseModel

from hello_sales_backend.app import create_app
from hello_sales_backend.platform.composition.overrides import AppOverrides
from hello_sales_backend.platform.config.settings import Settings, get_settings


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
        return cls(settings=settings or get_settings(), overrides=overrides)

    def build_app(self):
        """Build an application instance for the smoke run."""

        return create_app(self.settings, overrides=self.overrides)


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
