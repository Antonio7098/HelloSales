from __future__ import annotations

import pytest

from hello_sales_backend.platform.agents.tools import (
    AgentToolCatalog,
    AgentToolDefinition,
    AgentToolExecutionContext,
    EmptyToolArguments,
)
from hello_sales_backend.shared.errors import AppError


def _context(*, permissions: tuple[str, ...]) -> AgentToolExecutionContext:
    return AgentToolExecutionContext(
        request_id="request-1",
        trace_id="trace-1",
        actor_id="actor-1",
        org_id="org-1",
        permissions=permissions,
    )


@pytest.mark.asyncio
async def test_agent_tool_catalog_rejects_missing_required_permissions() -> None:
    catalog = AgentToolCatalog(
        [
            AgentToolDefinition(
                name="restricted_tool",
                description="Restricted test tool",
                arguments_model=EmptyToolArguments,
                execute=lambda _arguments, _context: {"ok": True},
                required_permissions=("restricted.use",),
            )
        ]
    )

    with pytest.raises(AppError) as exc_info:
        await catalog.execute(
            name="restricted_tool",
            arguments={},
            context=_context(permissions=()),
        )

    assert exc_info.value.code == "auth.permission_denied"
    assert exc_info.value.status_code == 403
    assert exc_info.value.details["missing_permissions"] == ["restricted.use"]


@pytest.mark.asyncio
async def test_agent_tool_catalog_executes_when_required_permissions_are_present() -> None:
    catalog = AgentToolCatalog(
        [
            AgentToolDefinition(
                name="restricted_tool",
                description="Restricted test tool",
                arguments_model=EmptyToolArguments,
                execute=lambda _arguments, _context: {"ok": True},
                required_permissions=("restricted.use",),
            )
        ]
    )

    result = await catalog.execute(
        name="restricted_tool",
        arguments={},
        context=_context(permissions=("restricted.use",)),
    )

    assert result == {"ok": True}
