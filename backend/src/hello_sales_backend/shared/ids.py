"""Shared ID helpers."""

from uuid import uuid4


def new_id() -> str:
    """Return a hex identifier."""

    return uuid4().hex
