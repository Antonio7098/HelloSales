from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        value = (v or "").strip()
        if not value:
            raise ValueError("Action type must be non-empty")
        return value


class AgentArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        value = (v or "").strip()
        if not value:
            raise ValueError("Artifact type must be non-empty")
        return value


class AgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assistant_message: str
    actions: list[AgentAction] = Field(default_factory=list)
    artifacts: list[AgentArtifact] = Field(default_factory=list)

    @field_validator("assistant_message")
    @classmethod
    def _validate_assistant_message(cls, v: str) -> str:
        value = (v or "").strip()
        if not value:
            raise ValueError("assistant_message must be non-empty")
        return value
