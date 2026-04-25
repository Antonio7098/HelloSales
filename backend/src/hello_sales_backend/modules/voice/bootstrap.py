"""Voice module bootstrap."""

from __future__ import annotations

from dataclasses import dataclass

from hello_sales_backend.modules.voice.use_cases.voice_service import VoiceService
from hello_sales_backend.platform.composition.providers import ProviderRegistry
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.observability.runtime import ObservabilityRuntime


@dataclass(slots=True)
class VoiceModule:
    """Voice module bundle."""

    service: VoiceService


def build_voice_module(
    *,
    settings: Settings,
    providers: ProviderRegistry,
    observability: ObservabilityRuntime,
) -> VoiceModule:
    """Build voice module services."""

    return VoiceModule(
        service=VoiceService(
            settings=settings,
            stt_provider=providers.voice_stt,
            tts_provider=providers.voice_tts,
            turn_detection=providers.voice_turn_detection,
            observability=observability,
        )
    )
