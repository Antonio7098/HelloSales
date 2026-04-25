"""Composition-time test and environment overrides."""

from __future__ import annotations

from dataclasses import dataclass

from hello_sales_backend.modules.system.use_cases.ports import ClockPort
from hello_sales_backend.platform.auth.contracts import AuthProviderPort
from hello_sales_backend.platform.llm.contracts import LLMProviderPort
from hello_sales_backend.platform.observability.runtime import ObservabilityRuntime
from hello_sales_backend.platform.tasks.models import TaskEventSink
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner
from hello_sales_backend.platform.voice.contracts import (
    RealtimeVoiceProviderPort,
    STTProviderPort,
    TTSProviderPort,
    TurnDetectionPort,
)
from hello_sales_backend.platform.web_search.contracts import WebSearchProviderPort
from hello_sales_backend.platform.workflows.runtime import WorkflowRuntime


@dataclass(slots=True)
class AppOverrides:
    """Override selected collaborators when building the app container."""

    auth_provider: AuthProviderPort | None = None
    llm_provider: LLMProviderPort | None = None
    web_search_provider: WebSearchProviderPort | None = None
    voice_stt_provider: STTProviderPort | None = None
    voice_tts_provider: TTSProviderPort | None = None
    voice_realtime_provider: RealtimeVoiceProviderPort | None = None
    voice_turn_detection_provider: TurnDetectionPort | None = None
    task_runner: BackgroundTaskRunner | None = None
    task_event_sink: TaskEventSink | None = None
    observability_runtime: ObservabilityRuntime | None = None
    workflow_runtime: WorkflowRuntime | None = None
    system_clock: ClockPort | None = None
