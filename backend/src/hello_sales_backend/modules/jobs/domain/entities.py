"""Jobs domain entities."""

from pydantic import BaseModel


class DiagnosticRunResult(BaseModel):
    """Result of a diagnostic workflow execution."""

    workflow_name: str
    provider: str
    model: str
    output_text: str
