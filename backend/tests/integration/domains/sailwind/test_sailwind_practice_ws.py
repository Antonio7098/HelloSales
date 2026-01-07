from __future__ import annotations

import queue
import threading
import uuid
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import get_session_context
from app.main import app
from app.models.sailwind_playbook import Client, Product, Strategy


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def _receive_json_with_timeout(websocket, timeout: float = 10.0):
    q: queue.Queue[object] = queue.Queue(maxsize=1)

    def _worker() -> None:
        try:
            q.put(websocket.receive_json())
        except Exception as exc:  # pragma: no cover
            q.put(exc)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise TimeoutError("Timed out waiting for websocket message")

    item = q.get_nowait()
    if isinstance(item, Exception):
        raise item
    return item


def _drain_until(websocket, predicate, max_messages: int = 200, timeout: float = 10.0):
    for _ in range(max_messages):
        msg = _receive_json_with_timeout(websocket, timeout=timeout)
        if predicate(msg):
            return msg
    raise AssertionError("Did not receive expected message")


@pytest.mark.asyncio
async def _seed_strategy(org_id: UUID) -> UUID:
    async with get_session_context() as db:
        product = Product(organization_id=org_id, name="Widget")
        client_row = Client(organization_id=org_id, name="Globex", industry="Tech")
        db.add_all([product, client_row])
        await db.flush()

        strategy = Strategy(
            organization_id=org_id,
            product_id=product.id,
            client_id=client_row.id,
            status="active",
            strategy_text="Lead with ROI",
        )
        db.add(strategy)
        await db.flush()
        return strategy.id


def test_sailwind_practice_ws_start_and_message_streams_tokens(client: TestClient, monkeypatch):
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "true")
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_123")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()

    org_workos_id = "org_practice_ws_123"

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_rep_practice_ws",
                "email": "rep@example.com",
                "org_id": org_workos_id,
                "role": "rep",
            }
        ),
    ), client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "auth", "payload": {"token": "workos_token"}})
        auth_msg = _receive_json_with_timeout(websocket, timeout=5.0)
        assert auth_msg["type"] == "auth.success"

        # consume initial status.update
        _receive_json_with_timeout(websocket, timeout=5.0)

        org_id = UUID(auth_msg["payload"]["orgId"])
        strategy_id = client.portal.call(_seed_strategy, org_id)

        start_request_id = str(uuid.uuid4())
        websocket.send_json(
            {
                "type": "sailwind.practice.start",
                "payload": {
                    "strategyId": str(strategy_id),
                    "requestId": start_request_id,
                },
            }
        )

        started = _drain_until(websocket, lambda m: m.get("type") == "sailwind.practice.started")
        practice_session_id = started["payload"]["practiceSessionId"]

        msg_request_id = str(uuid.uuid4())
        websocket.send_json(
            {
                "type": "sailwind.practice.message",
                "payload": {
                    "practiceSessionId": practice_session_id,
                    "content": "hello",
                    "requestId": msg_request_id,
                },
            }
        )

        _drain_until(
            websocket,
            lambda m: m.get("type") == "status.update"
            and m.get("payload", {}).get("service") == "pipeline"
            and m.get("payload", {}).get("status") == "running",
        )

        tokens: list[str] = []
        complete_msg = None
        for _ in range(160):
            msg = _receive_json_with_timeout(websocket, timeout=5.0)
            if msg.get("type") == "chat.token":
                tokens.append(msg["payload"]["token"])
            if msg.get("type") == "chat.complete":
                complete_msg = msg
                break

        assert complete_msg is not None
        assert complete_msg["payload"].get("practiceSessionId") == practice_session_id
        assert complete_msg["payload"]["content"] == "".join(tokens)


def test_sailwind_practice_ws_requires_auth(client: TestClient, monkeypatch):
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json(
            {
                "type": "sailwind.practice.start",
                "payload": {"strategyId": str(uuid.uuid4()), "requestId": str(uuid.uuid4())},
            }
        )
        resp = _receive_json_with_timeout(websocket, timeout=5.0)
        assert resp["type"] == "error"
        assert resp["payload"]["code"] == "NOT_AUTHENTICATED"
