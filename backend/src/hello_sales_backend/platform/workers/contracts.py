"""Platform-owned worker definition contracts."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from pydantic import BaseModel

from hello_sales_backend.platform.llm import EffectivePromptRef, LLMMessage


class WorkerDefinitionPort(Protocol):
    """Concrete worker contract consumed by the runtime."""

    @property
    def worker_name(self) -> str: ...

    @property
    def input_model(self) -> type[BaseModel]: ...

    @property
    def output_model(self) -> type[BaseModel]: ...

    @property
    def max_attempts(self) -> int: ...

    @property
    def timeout_seconds(self) -> float: ...

    @property
    def use_backup_on_final_attempt(self) -> bool: ...

    @property
    def validate_output(self) -> Callable[[BaseModel], None] | None: ...

    @property
    def prompt(self) -> object: ...

    def build_messages(self, validated_input: BaseModel, retry_issue: str | None) -> list[LLMMessage]: ...

    def effective_prompt_ref(self) -> EffectivePromptRef: ...


class WorkerRegistryPort(Protocol):
    """Resolve concrete worker definitions for the runtime."""

    def require(self, worker_name: str) -> WorkerDefinitionPort: ...
