"""Jobs commands."""

from pydantic import BaseModel


class StartDiagnosticJobCommand(BaseModel):
    """Start a minimal provider-orchestration diagnostic run."""

    prompt: str = "Reply with the single word OK."
