"""Stageflow integration for the HelloSales backend.

This module provides stageflow-based pipeline implementations for chat,
replacing the older substrate-based pipeline system.
"""

from app.ai.stageflow.events import WebSocketEventSink
from app.ai.stageflow.pipeline import (
    create_chat_pipeline,
    create_simple_chat_pipeline,
    ChatPipelineRunner,
    get_chat_pipeline_runner,
)
from app.ai.stageflow.stages import (
    ChatRouterStage,
    ChatLLMStage,
    ChatLLMStreamStage,
    ChatPersistStage,
    ChatUserPersistStage,
)

__all__ = [
    # Events
    "WebSocketEventSink",
    # Pipeline
    "create_chat_pipeline",
    "create_simple_chat_pipeline",
    "ChatPipelineRunner",
    "get_chat_pipeline_runner",
    # Stages
    "ChatRouterStage",
    "ChatLLMStage",
    "ChatLLMStreamStage",
    "ChatPersistStage",
    "ChatUserPersistStage",
]
