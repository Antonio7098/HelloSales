"""Shared smoke helpers."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI


@asynccontextmanager
async def app_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """Yield an in-process client with application lifespan enabled."""

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=True)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client


async def wait_for_terminal_run_state(
    client: httpx.AsyncClient,
    *,
    path: str,
    attempts: int = 60,
    delay_seconds: float = 0.25,
    terminal_statuses: set[str] | None = None,
) -> dict[str, object]:
    """Poll a run resource until it reaches a terminal state."""

    target_statuses = terminal_statuses or {"awaiting_approval", "completed", "failed", "cancelled"}
    for _ in range(attempts):
        response = await client.get(path)
        response.raise_for_status()
        payload = response.json()["data"]
        if payload["status"] in target_statuses:
            return payload
        await asyncio.sleep(delay_seconds)
    return {"status": "timeout"}


def parse_sse_events(body: str) -> list[dict[str, object]]:
    """Parse a text/event-stream payload into structured entries."""

    parsed: list[dict[str, object]] = []
    for chunk in body.strip().split("\n\n"):
        if not chunk.strip():
            continue
        entry: dict[str, object] = {}
        for line in chunk.splitlines():
            if line.startswith("id: "):
                entry["id"] = int(line.removeprefix("id: "))
            elif line.startswith("event: "):
                entry["event"] = line.removeprefix("event: ")
            elif line.startswith("data: "):
                entry["data"] = json.loads(line.removeprefix("data: "))
        parsed.append(entry)
    return parsed
