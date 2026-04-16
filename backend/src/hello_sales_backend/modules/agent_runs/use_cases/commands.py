"""Agent-runs command DTOs."""

from pydantic import BaseModel, Field


class StartAgentRunCommand(BaseModel):
    """Start a new agent run with an initial turn."""

    input_text: str = Field(min_length=1)
    profile_name: str = Field(default="generic", min_length=1)


class AppendAgentTurnCommand(BaseModel):
    """Append a new turn to an existing agent run."""

    input_text: str = Field(min_length=1)


class ApprovalDecisionCommand(BaseModel):
    """Approve or reject a pending tool call."""

    approved: bool
