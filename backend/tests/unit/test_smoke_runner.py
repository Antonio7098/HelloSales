from __future__ import annotations

from pydantic import BaseModel
import pytest

from hello_sales_backend.shared.errors import AppError
from hello_sales_backend.smoke.contracts import SmokeCase, SmokeContext
from hello_sales_backend.smoke.registry import SmokeRegistry
from hello_sales_backend.smoke.runner import SmokeRunner


class ExampleSmokeResult(BaseModel):
    status: str
    value: str


class ExampleSmoke(SmokeCase):
    name = "example"
    description = "example smoke"

    async def run(self, context: SmokeContext) -> BaseModel:
        return ExampleSmokeResult(status="completed", value=context.settings.environment)


@pytest.mark.asyncio
async def test_smoke_runner_executes_registered_smoke(test_settings):
    runner = SmokeRunner(SmokeRegistry([ExampleSmoke()]), SmokeContext.create(settings=test_settings))

    result = await runner.run()

    assert result.smoke_name == "example"
    assert result.payload["status"] == "completed"
    assert result.payload["value"] == "test"


def test_smoke_registry_rejects_unknown_name():
    registry = SmokeRegistry([ExampleSmoke()])

    with pytest.raises(AppError) as exc_info:
        registry.get("missing")

    assert exc_info.value.code == "smoke.target.unknown"
