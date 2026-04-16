"""System commands."""

from pydantic import BaseModel


class ReadSystemStatusCommand(BaseModel):
    """Read the current runtime status."""

    include_runtime_details: bool = True
