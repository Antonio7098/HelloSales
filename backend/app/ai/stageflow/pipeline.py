"""Chat pipeline using stageflow.

This module provides stageflow-based pipeline implementations for chat.
"""

import logging
from uuid import UUID
from datetime import datetime

from stageflow import Pipeline, StageKind

from app.ai.stageflow.stages import (
    ChatRouterStage,
    ChatLLMStreamStage,
    ChatPersistStage,
    ChatUserPersistStage,
)
from app.ai.stageflow.events import WebSocketEventSink

logger = logging.getLogger("chat")


def create_chat_pipeline() -> Pipeline:
    """Create a basic chat pipeline using stageflow.

    Pipeline DAG:
        [user_persist] → [router] → [llm_stream] → [persist]

    This is a simple pipeline for basic chat without enrichers.
    The router stage can be extended to branch to different behaviors.
    """
    return (
        Pipeline()
        .with_stage(
            name="user_persist",
            runner=ChatUserPersistStage,
            kind=StageKind.WORK,
        )
        .with_stage(
            name="router",
            runner=ChatRouterStage,
            kind=StageKind.ROUTE,
            dependencies=("user_persist",),
        )
        .with_stage(
            name="llm_stream",
            runner=ChatLLMStreamStage,
            kind=StageKind.TRANSFORM,
            dependencies=("router",),
        )
        .with_stage(
            name="persist",
            runner=ChatPersistStage,
            kind=StageKind.WORK,
            dependencies=("llm_stream",),
        )
    )


def create_simple_chat_pipeline() -> Pipeline:
    """Create an even simpler chat pipeline (no persistence stages).

    Pipeline DAG:
        [router] → [llm_stream]

    This is for when persistence is handled separately.
    """
    return (
        Pipeline()
        .with_stage(
            name="router",
            runner=ChatRouterStage,
            kind=StageKind.ROUTE,
        )
        .with_stage(
            name="llm_stream",
            runner=ChatLLMStreamStage,
            kind=StageKind.TRANSFORM,
            dependencies=("router",),
        )
    )


class ChatPipelineRunner:
    """Runner for stageflow chat pipelines.

    This class manages the pipeline lifecycle and integrates with
    the WebSocket connection manager for event emission.
    """

    def __init__(self, event_sink: WebSocketEventSink | None = None):
        """Initialize the pipeline runner.

        Args:
            event_sink: Optional event sink. Defaults to WebSocketEventSink.
        """
        self._event_sink = event_sink or WebSocketEventSink()
        self._pipeline = create_chat_pipeline()
        self._graph = self._pipeline.build()

    async def run(
        self,
        *,
        pipeline_run_id: UUID,
        request_id: UUID,
        session_id: UUID,
        user_id: UUID,
        interaction_id: UUID,
        input_text: str,
        messages: list | None = None,
        org_id: UUID | None = None,
        topology: str = "chat",
        execution_mode: str = "default",
    ) -> dict:
        """Run the chat pipeline.

        Args:
            pipeline_run_id: Unique identifier for this pipeline run
            request_id: HTTP/WebSocket request identifier
            session_id: User session identifier
            user_id: User identifier
            interaction_id: Interaction identifier
            input_text: User input text
            messages: Optional conversation history
            org_id: Optional organization/tenant identifier
            topology: Pipeline topology name
            execution_mode: Execution mode (default, practice, etc.)

        Returns:
            Dictionary of stage results
        """
        from stageflow.context import ContextSnapshot, Message

        # Create context snapshot
        snapshot = ContextSnapshot(
            pipeline_run_id=pipeline_run_id,
            request_id=request_id,
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            interaction_id=interaction_id,
            topology=topology,
            execution_mode=execution_mode,
            input_text=input_text,
            messages=[
                Message(
                    role=m["role"],
                    content=m["content"],
                    timestamp=datetime.fromisoformat(m["timestamp"])
                )
                for m in (messages or [])
                if isinstance(m, dict)
            ] if messages else [],
        )

        # Create stage context
        ctx = StageContext(snapshot=snapshot)

        # Set event sink if available
        ctx.event_sink = self._event_sink

        logger.info(
            "Starting chat pipeline",
            extra={
                "service": "chat",
                "pipeline_run_id": str(pipeline_run_id),
                "session_id": str(session_id),
                "input_length": len(input_text),
            },
        )

        # Run the pipeline
        results = await self._graph.run(ctx)

        logger.info(
            "Chat pipeline completed",
            extra={
                "service": "chat",
                "pipeline_run_id": str(pipeline_run_id),
                "stages_completed": len(results),
            },
        )

        return results

    async def run_simple(
        self,
        *,
        pipeline_run_id: UUID,
        request_id: UUID,
        session_id: UUID,
        user_id: UUID,
        interaction_id: UUID,
        input_text: str,
        messages: list | None = None,
        org_id: UUID | None = None,
    ) -> dict:
        """Run the simple chat pipeline (no persistence).

        Args:
            pipeline_run_id: Unique identifier for this pipeline run
            request_id: HTTP/WebSocket request identifier
            session_id: User session identifier
            user_id: User identifier
            interaction_id: Interaction identifier
            input_text: User input text
            messages: Optional conversation history
            org_id: Optional organization/tenant identifier

        Returns:
            Dictionary of stage results
        """
        from stageflow.context import ContextSnapshot, Message

        # Create context snapshot
        snapshot = ContextSnapshot(
            pipeline_run_id=pipeline_run_id,
            request_id=request_id,
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            interaction_id=interaction_id,
            topology="chat_simple",
            execution_mode="default",
            input_text=input_text,
            messages=[
                Message(
                    role=m["role"],
                    content=m["content"],
                    timestamp=datetime.fromisoformat(m["timestamp"])
                )
                for m in (messages or [])
                if isinstance(m, dict)
            ] if messages else [],
        )

        # Create stage context
        ctx = StageContext(snapshot=snapshot)

        # Set event sink if available
        ctx.event_sink = self._event_sink

        # Build and run simple pipeline
        pipeline = create_simple_chat_pipeline()
        graph = pipeline.build()

        logger.info(
            "Starting simple chat pipeline",
            extra={
                "service": "chat",
                "pipeline_run_id": str(pipeline_run_id),
                "input_length": len(input_text),
            },
        )

        results = await graph.run(ctx)

        logger.info(
            "Simple chat pipeline completed",
            extra={
                "service": "chat",
                "pipeline_run_id": str(pipeline_run_id),
                "stages_completed": len(results),
            },
        )

        return results


# Global pipeline runner instance
_chat_pipeline_runner: ChatPipelineRunner | None = None


def get_chat_pipeline_runner() -> ChatPipelineRunner:
    """Get the global chat pipeline runner instance."""
    global _chat_pipeline_runner
    if _chat_pipeline_runner is None:
        _chat_pipeline_runner = ChatPipelineRunner()
    return _chat_pipeline_runner


def reset_chat_pipeline_runner() -> None:
    """Reset the global chat pipeline runner (for testing)."""
    global _chat_pipeline_runner
    _chat_pipeline_runner = None
