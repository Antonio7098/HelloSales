"""Voice module ports."""

from hello_sales_backend.platform.voice import (
    RealtimeVoiceProviderPort,
    STTProviderPort,
    TTSProviderPort,
    TurnDetectionPort,
    VoiceTransportPort,
)

__all__ = [
    "RealtimeVoiceProviderPort",
    "STTProviderPort",
    "TTSProviderPort",
    "TurnDetectionPort",
    "VoiceTransportPort",
]
