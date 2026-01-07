"""Eloquence-specific pipeline definitions.

This module contains the concrete pipeline classes for all Eloquence pipelines:
- ChatFastPipeline
- ChatAccuratePipeline
- VoiceFastPipeline
- VoiceAccuratePipeline

Pipelines are registered via register_all_pipelines() which should be called
at application startup after all modules are loaded.
"""

from __future__ import annotations

from .definitions import (
    ChatAccuratePipeline,
    ChatFastPipeline,
    VoiceAccuratePipeline,
    VoiceFastPipeline,
    register_all_pipelines,
)

__all__ = [
    "ChatFastPipeline",
    "ChatAccuratePipeline",
    "VoiceFastPipeline",
    "VoiceAccuratePipeline",
    "register_all_pipelines",
]
