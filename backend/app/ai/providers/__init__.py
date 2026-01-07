"""AI provider implementations.

This module contains LLM, STT, and TTS provider implementations.
"""

from app.ai.providers.base import (
    LLMMessage,
    LLMProvider,
    LLMResponse,
    STTProvider,
    STTResult,
    TTSProvider,
    TTSResult,
)
from app.ai.providers.factory import get_llm_provider, get_stt_provider, get_tts_provider
from app.ai.providers.llm import GeminiProvider, GroqProvider, OpenRouterProvider
from app.ai.providers.llm.stub import StubLLMProvider, StubSTTProvider, StubTTSProvider
from app.ai.providers.stt import (
    DeepgramFluxSTTProvider,
    DeepgramSTTProvider,
    GoogleSTTProvider,
    GroqWhisperSTTProvider,
)
from app.ai.providers.tts import GoogleTTSProvider

# Backward compatibility aliases
StubProvider = StubLLMProvider
GeminiTTSProvider = GoogleTTSProvider  # Gemini TTS uses Google provider internally

__all__ = [
    "get_llm_provider",
    "get_stt_provider",
    "get_tts_provider",
    "LLMProvider",
    "STTProvider",
    "TTSProvider",
    "LLMMessage",
    "LLMResponse",
    "STTResult",
    "TTSResult",
    "GroqProvider",
    "GeminiProvider",
    "OpenRouterProvider",
    "StubLLMProvider",
    "StubSTTProvider",
    "StubTTSProvider",
    # Backward compatibility
    "StubProvider",
    "DeepgramSTTProvider",
    "DeepgramFluxSTTProvider",
    "GoogleSTTProvider",
    "GroqWhisperSTTProvider",
    "GoogleTTSProvider",
    # Backward compatibility
    "GeminiTTSProvider",
]
