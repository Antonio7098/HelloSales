"""Application-level worker definition contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel

from hello_sales_backend.platform.llm import LLMMessage


class WorkerSemanticValidator(Protocol):
    """Validate a parsed worker output model."""

    def __call__(self, output_model: BaseModel) -> None: ...


WorkerMessageBuilder = Callable[[BaseModel, str | None], list[LLMMessage]]


@dataclass(slots=True, frozen=True)
class WorkerDefinition:
    """Concrete application worker configuration."""

    worker_name: str
    display_name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    build_messages: WorkerMessageBuilder
    validate_output: WorkerSemanticValidator | None = None
    max_attempts: int = 2
    timeout_seconds: float = 30.0
    use_backup_on_final_attempt: bool = True
