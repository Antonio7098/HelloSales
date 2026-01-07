"""Event bus system for structured event logging.

This module provides an EventBus class for publishing and subscribing
to events across the application. It supports async event handlers
and structured event data.

Design:
- Async event bus for decoupled communication
- Structured event data with type and payload
- Handler registration by event type
- Error handling with continue-on-error policy

Usage:
    # Publish an event
    await event_bus.emit("user.created", {"user_id": "123"})

    # Subscribe to events
    @event_bus.on("user.created")
    async def handle_user_created(data):
        logger.info(f"User created: {data['user_id']}")
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import uuid4


class EventHandler(Protocol):
    """Protocol for async event handlers."""

    async def __call__(self, event_type: str, data: dict[str, Any]) -> None:
        ...


@dataclass
class Event:
    """Event data structure.

    Attributes:
        id: Unique event identifier
        type: Event type identifier (e.g., "session_state.created")
        data: Event payload
        timestamp: When the event was created
        metadata: Additional context (source, correlation_id, etc.)
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    type: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class EventBus:
    """Event bus for publish-subscribe communication.

    Provides async event publishing and handler registration.

    Attributes:
        handlers: Mapping of event type to list of handlers
        default_handler: Optional default handler for all events
    """

    def __init__(
        self,
        default_handler: EventHandler | None = None,
    ) -> None:
        """Initialize the event bus.

        Args:
            default_handler: Optional handler called for all events
        """
        self._handlers: dict[str, list[EventHandler]] = {}
        self._default_handler = default_handler
        self._closed = False

    def on(
        self,
        event_type: str,
    ) -> Callable[[EventHandler], EventHandler]:
        """Decorator to register an event handler.

        Args:
            event_type: The event type to subscribe to

        Returns:
            Decorator function

        Example:
            @event_bus.on("session_state.created")
            async def handle_created(event_type, data):
                print(f"Session state created: {data['session_id']}")
        """
        def decorator(handler: EventHandler) -> EventHandler:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            return handler
        return decorator

    def off(
        self,
        event_type: str,
        handler: EventHandler | None = None,
    ) -> None:
        """Unregister event handlers.

        Args:
            event_type: The event type
            handler: Specific handler to remove, or None to remove all
        """
        if handler is None:
            self._handlers.pop(event_type, None)
        else:
            handlers = self._handlers.get(event_type, [])
            self._handlers[event_type] = [
                h for h in handlers if h != handler
            ]

    async def emit(
        self,
        event_type: str,
        data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Publish an event.

        Args:
            event_type: The event type identifier
            data: Event payload
            metadata: Additional context

        Returns:
            List of handler return values

        Example:
            await event_bus.emit(
                "session_state.updated",
                {"session_id": "123", "behavior": "onboarding"}
            )
        """
        event = Event(
            type=event_type,
            data=data,
            metadata=metadata or {},
        )

        results = []
        handlers = self._handlers.get(event_type, [])[:]

        if self._default_handler:
            handlers.append(self._default_handler)

        for handler in handlers:
            try:
                result = await handler(event.type, event.data)
                results.append(result)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f"Event handler failed: {event_type}",
                    exc_info=e,
                )

        return results

    async def emit_event(self, event: Event) -> list[Any]:
        """Publish a pre-built Event object.

        Args:
            event: The Event to publish

        Returns:
            List of handler return values
        """
        return await self.emit(
            event.type,
            event.data,
            event.metadata,
        )

    def get_handlers(self, event_type: str) -> list[EventHandler]:
        """Get registered handlers for an event type.

        Args:
            event_type: The event type

        Returns:
            List of handlers
        """
        return self._handlers.get(event_type, [])[:]

    async def close(self) -> None:
        """Close the event bus and cleanup handlers."""
        self._handlers.clear()
        self._closed = True


class NullEventBus(EventBus):
    """Null implementation of EventBus for testing.

    Silently discards all events.
    """

    async def emit(
        self,
        _event_type: str,
        _data: dict[str, Any],
        _metadata: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Discard the event."""
        return []

    async def emit_event(self, _event: Event) -> list[Any]:
        """Discard the event."""
        return []


# Global event bus instance
event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Get the global event bus instance.

    Returns:
        The global EventBus instance
    """
    return event_bus


def set_event_bus(bus: EventBus) -> None:
    """Set the global event bus instance.

    Args:
        bus: The EventBus to use globally
    """
    global event_bus
    event_bus = bus


__all__ = [
    "Event",
    "EventBus",
    "EventHandler",
    "NullEventBus",
    "event_bus",
    "get_event_bus",
    "set_event_bus",
]
