"""Generic structured brief worker definition."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from hello_sales_backend.application.workers.contracts import (
    WorkerDefinition,
    WorkerPromptDefinition,
)
from hello_sales_backend.platform.llm import LLMMessage, PromptMetadata


class StructuredBriefInput(BaseModel):
    """Input payload for the scaffold-stage worker."""

    text: str = Field(min_length=1)
    goal: str = Field(default="Produce a concise structured brief", min_length=1)


class StructuredBriefOutput(BaseModel):
    """Structured result expected from the worker."""

    brief: str = Field(min_length=1)
    key_points: list[str] = Field(min_length=1)
    priority: Literal["low", "medium", "high"]


def build_messages_v1(validated_input: BaseModel, retry_issue: str | None) -> list[LLMMessage]:
    """Build the versioned structured-brief generation prompt."""

    payload = StructuredBriefInput.model_validate(validated_input.model_dump(mode="json"))
    instructions = [
        "Return only JSON that satisfies the provided schema.",
        "Do not add markdown, commentary, or prose outside the JSON object.",
        f"Goal: {payload.goal}",
        f"Text: {payload.text}",
        "Choose `priority` based on urgency implied by the text.",
    ]
    if retry_issue is not None:
        instructions.append(f"Previous output issue: {retry_issue}")
    return [LLMMessage(role="user", content="\n".join(instructions))]


STRUCTURED_BRIEF_GENERATION_PROMPT = WorkerPromptDefinition(
    metadata=PromptMetadata(
        prompt_id="worker.structured-brief.generation",
        version="v1",
        owner_kind="worker",
        owner_id="structured-brief",
        purpose="generation",
    ),
    build_messages=build_messages_v1,
)


def build_structured_brief_definition() -> WorkerDefinition:
    """Return the default generic worker used for end-to-end coverage."""

    return WorkerDefinition(
        worker_name="structured-brief",
        display_name="Structured Brief",
        description="Generate a generic structured brief from free-form text.",
        input_model=StructuredBriefInput,
        output_model=StructuredBriefOutput,
        prompt=STRUCTURED_BRIEF_GENERATION_PROMPT,
        max_attempts=3,
        timeout_seconds=20.0,
        use_backup_on_final_attempt=True,
    )
