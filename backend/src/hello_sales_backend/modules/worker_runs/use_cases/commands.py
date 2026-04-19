"""Worker-runs command DTOs."""

from pydantic import BaseModel, Field


class StartWorkerRunCommand(BaseModel):
    """Start a new worker run."""

    worker_name: str = Field(min_length=1)
    input_payload: dict[str, object]
    execution_mode: str = Field(default="direct", pattern="^(direct|stageflow)$")
    timeout_seconds: float | None = Field(default=None, gt=0)
    max_attempts: int | None = Field(default=None, ge=1, le=5)
