"""System value objects."""

from pydantic import BaseModel


class UtcTimestamp(BaseModel):
    """UTC timestamp value object."""

    iso_value: str
