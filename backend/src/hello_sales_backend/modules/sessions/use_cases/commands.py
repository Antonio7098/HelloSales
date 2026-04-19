"""Session command DTOs."""

from pydantic import BaseModel, Field


class CreateSessionCommand(BaseModel):
    """Create a new session and append the first user message."""

    input_text: str = Field(min_length=1)
    profile_name: str = Field(default="generic", min_length=1)
    user_id: str | None = None
    org_id: str | None = None


class AppendSessionMessageCommand(BaseModel):
    """Append a new user message to an existing session."""

    input_text: str = Field(min_length=1)

