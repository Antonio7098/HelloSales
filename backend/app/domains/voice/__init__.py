"""Voice domain - handles voice-to-voice conversations.

Services:
    - VoiceService: Main voice service (orchestration + recording management)

Specialized Services (SRP-compliant):
    - RecordingManager: Manages audio recording state
    - VoicePipelineOrchestrator: Orchestrates the full STT -> LLM -> TTS pipeline
"""

from app.domains.voice.service import VoiceService
from app.domains.voice.services import (
    RecordingManager,
    VoicePipelineOrchestrator,
)

__all__ = [
    "VoiceService",
    "RecordingManager",
    "VoicePipelineOrchestrator",
]
