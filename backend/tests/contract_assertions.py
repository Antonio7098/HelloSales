from __future__ import annotations

import queue
import threading
from collections.abc import Callable, Sequence
from typing import Any


def receive_json_with_timeout(websocket: Any, timeout: float = 30.0) -> Any:
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


def drain_until(
    websocket: Any,
    predicate: Callable[[Any], bool],
    *,
    max_messages: int = 200,
    timeout: float = 30.0,
) -> Any:
    for _ in range(max_messages):
        msg = receive_json_with_timeout(websocket, timeout=timeout)
        if predicate(msg):
            return msg
    raise AssertionError("Did not receive expected message")


def _timeline_types(items: Sequence[Any]) -> str:
    parts: list[str] = []
    for item in items:
        if isinstance(item, dict):
            t = item.get("type")
            if isinstance(t, str):
                parts.append(t)
                continue
        parts.append(type(item).__name__)
    return ", ".join(parts)


def assert_pipeline_event_types_contains(
    event_types: Sequence[str],
    *,
    required: Sequence[str],
    forbidden: Sequence[str] | None = None,
) -> None:
    required_set = set(required)
    observed_set = set(event_types)

    missing = sorted(required_set - observed_set)
    if missing:
        raise AssertionError(
            "Missing pipeline event types: "
            + ", ".join(missing)
            + "\nObserved: "
            + ", ".join(event_types)
        )

    if forbidden:
        forbidden_set = set(forbidden)
        present = sorted(forbidden_set & observed_set)
        if present:
            raise AssertionError(
                "Forbidden pipeline event types present: "
                + ", ".join(present)
                + "\nObserved: "
                + ", ".join(event_types)
            )


def assert_ws_messages_exactly_one_chat_complete(
    messages: Sequence[dict[str, Any]],
    *,
    request_id: str,
    pipeline_run_id: str,
) -> None:
    completes: list[dict[str, Any]] = []
    for msg in messages:
        if msg.get("type") != "chat.complete":
            continue
        md = msg.get("metadata")
        if not isinstance(md, dict):
            continue
        if md.get("request_id") != request_id:
            continue
        if md.get("pipeline_run_id") != pipeline_run_id:
            continue
        completes.append(msg)

    if len(completes) != 1:
        raise AssertionError(
            f"Expected exactly 1 chat.complete for request_id={request_id} "
            f"pipeline_run_id={pipeline_run_id}, observed {len(completes)}. "
            f"Timeline types: [{_timeline_types(messages)}]"
        )


def assert_websocket_no_chat_complete(
    websocket: Any,
    *,
    max_messages: int = 30,
    timeout: float = 1.0,
) -> None:
    for _ in range(max_messages):
        try:
            msg = receive_json_with_timeout(websocket, timeout=timeout)
        except TimeoutError:
            return

        if isinstance(msg, dict) and msg.get("type") == "chat.complete":
            raise AssertionError("Received unexpected chat.complete after cancellation")


async def assert_pipeline_run_terminal_status(
    db_session: Any,
    *,
    pipeline_run_id: Any,
    allowed_statuses: Sequence[str] = ("completed", "failed", "canceled"),
) -> None:
    from app.models.observability import PipelineRun

    run = await db_session.get(PipelineRun, pipeline_run_id)
    if run is None:
        raise AssertionError(f"pipeline_runs row missing for pipeline_run_id={pipeline_run_id}")

    if run.status not in set(allowed_statuses):
        raise AssertionError(
            f"pipeline_runs.status is not terminal for pipeline_run_id={pipeline_run_id}. "
            f"Observed status={run.status!r}, allowed={list(allowed_statuses)}"
        )


async def assert_pipeline_events_minimal_durability(
    db_session: Any,
    *,
    pipeline_run_id: Any,
) -> None:
    from sqlalchemy import select

    from app.models.observability import PipelineEvent

    events_result = await db_session.execute(
        select(PipelineEvent)
        .where(PipelineEvent.pipeline_run_id == pipeline_run_id)
        .order_by(PipelineEvent.timestamp.asc())
    )
    events = list(events_result.scalars().all())
    event_types = [e.type for e in events]

    assert_pipeline_event_types_contains(
        event_types,
        required=("pipeline.created", "pipeline.started"),
    )

    terminal_types = {"pipeline.completed", "pipeline.failed", "pipeline.canceled"}
    if not terminal_types.intersection(set(event_types)):
        raise AssertionError(
            "Missing terminal pipeline event type. "
            + f"Expected one of {sorted(terminal_types)}, observed: {event_types}"
        )
