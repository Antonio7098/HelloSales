"""First-class prompt identity contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PromptOwnerKind = Literal["agent", "worker", "session"]


@dataclass(slots=True, frozen=True)
class PromptMetadata:
    """Immutable metadata for one concrete prompt asset."""

    prompt_id: str
    version: str
    owner_kind: PromptOwnerKind
    owner_id: str
    purpose: str
    checksum: str | None = None


@dataclass(slots=True, frozen=True)
class EffectivePromptRef:
    """Runtime reference to the concrete prompt revision used for execution."""

    prompt_id: str
    version: str
    owner_kind: PromptOwnerKind
    owner_id: str
    purpose: str
    checksum: str | None = None


def effective_prompt_ref(metadata: PromptMetadata) -> EffectivePromptRef:
    """Project immutable prompt metadata into a runtime prompt reference."""

    return EffectivePromptRef(
        prompt_id=metadata.prompt_id,
        version=metadata.version,
        owner_kind=metadata.owner_kind,
        owner_id=metadata.owner_id,
        purpose=metadata.purpose,
        checksum=metadata.checksum,
    )
