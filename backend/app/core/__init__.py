"""Core module for DI container and other core utilities."""

from dataclasses import dataclass

from app.ai.providers import (
    get_llm_provider,
    get_stt_provider,
    get_tts_provider,
)
from app.ai.providers.base import (
    LLMProvider,
    STTProvider,
    TTSProvider,
)


@dataclass
class Container:
    """DI container for AI providers."""

    llm_provider: LLMProvider
    stt_provider: STTProvider
    tts_provider: TTSProvider


def get_container() -> Container:
    """Get the DI container with provider instances."""
    return Container(
        llm_provider=get_llm_provider(),
        stt_provider=get_stt_provider(),
        tts_provider=get_tts_provider(),
    )
