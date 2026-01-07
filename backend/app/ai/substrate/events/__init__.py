from typing import Any

from app.ai.substrate.events.sink import (
    DbPipelineEventSink,
    EventSink,
    NoOpEventSink,
    clear_event_sink,
    get_event_sink,
    set_event_sink,
    wait_for_event_sink_tasks,
)

# Backward compatibility aliases
register_event_sink = set_event_sink


async def emit_event(*, type: str, data: dict[str, Any] | None) -> None:
    """Emit an event through the current event sink."""
    sink = get_event_sink()
    if hasattr(sink, 'emit'):
        await sink.emit(type=type, data=data)


__all__ = [
    "EventSink",
    "NoOpEventSink",
    "DbPipelineEventSink",
    "get_event_sink",
    "set_event_sink",
    "clear_event_sink",
    "wait_for_event_sink_tasks",
    # Backward compatibility
    "register_event_sink",
    "emit_event",
]
