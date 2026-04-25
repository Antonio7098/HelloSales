"""Voice application module."""

from hello_sales_backend.modules.voice.bootstrap import VoiceModule, build_voice_module
from hello_sales_backend.modules.voice.use_cases.voice_service import VoiceService

__all__ = ["VoiceModule", "VoiceService", "build_voice_module"]
