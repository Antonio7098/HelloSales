"""Application-level worker definition contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel

from hello_sales_backend.platform.llm import (
    EffectivePromptRef,
    LLMMessage,
    PromptMetadata,
    effective_prompt_ref,
)


class WorkerSemanticValidator(Protocol):
    """Validate a parsed worker output model."""

    def __call__(self, output_model: BaseModel) -> None: ...


WorkerMessageBuilder = Callable[[BaseModel, str | None], list[LLMMessage]]


@dataclass(slots=True, frozen=True)
class WorkerPromptDefinition:
    """First-class prompt definition for one worker capability."""

    metadata: PromptMetadata
    build_messages: WorkerMessageBuilder

    @property
    def effective_prompt(self) -> EffectivePromptRef:
        return effective_prompt_ref(self.metadata)


@dataclass(slots=True, frozen=True)
class WorkerDefinition:
    """Concrete application worker configuration."""

    worker_name: str
    display_name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    prompt: WorkerPromptDefinition
    validate_output: WorkerSemanticValidator | None = None
    supports_direct_execution: bool = True
    max_attempts: int = 2
    timeout_seconds: float = 30.0
    use_backup_on_final_attempt: bool = True

    def build_messages(self, validated_input: BaseModel, retry_issue: str | None) -> list[LLMMessage]:
        return self.prompt.build_messages(validated_input, retry_issue)

    def effective_prompt_ref(self) -> EffectivePromptRef:
        return self.prompt.effective_prompt
