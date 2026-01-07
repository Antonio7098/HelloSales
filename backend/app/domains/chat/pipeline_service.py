"""ChatPipelineService for DAG-based chat operations.

This service handles the DAG/pipeline-based approach to chat message processing,
separating pipeline orchestration from core chat operations (which remain in ChatService).

Usage:
    from app.domains.chat.pipeline_service import ChatPipelineService

    pipeline_service = ChatPipelineService(chat_service, db)
    response, message_id = await pipeline_service.handle_message_dag(...)
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.substrate.agent.context_snapshot import ContextSnapshot
from app.ai.substrate.events import get_event_sink
from app.ai.substrate.stages import (
    PipelineContext,
    PipelineOrchestrator,
    StageExecutionError,
    extract_quality_mode,
)
from app.ai.substrate.stages.base import create_stage_context
from app.ai.substrate.stages.inputs import create_stage_inputs
from app.ai.substrate.stages.ports import create_stage_ports
from app.domains.chat.service import ChatContext, ChatService
from app.schemas.skill import SkillContextForLLM

if TYPE_CHECKING:
    pass

logger = logging.getLogger("chat_pipeline")


@dataclass
class PipelineOutput:
    """Output from chat pipeline execution."""
    full_text: str
    assistant_message_id: uuid.UUID
    metrics: dict[str, Any] | None = None


class ChatPipelineService:
    """Service for handling chat messages using DAG-based pipeline orchestration.

    This service is responsible for:
    - Agent routing to select appropriate pipeline topology/behavior
    - PipelineFactory integration for stage graph creation
    - PipelineOrchestrator lifecycle management
    - Pipeline run metrics and observability

    Core chat operations (context building, persistence, LLM streaming) are
    delegated to ChatService.
    """

    def __init__(
        self,
        chat_service: ChatService,
        db: AsyncSession,
    ) -> None:
        """Initialize pipeline service.

        Args:
            chat_service: ChatService instance for core operations
            db: Database session
        """
        self._chat_service = chat_service
        self.db = db

    async def handle_message_dag(
        self,
        content: str,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        message_id: uuid.UUID | None = None,
        assistant_message_id: uuid.UUID | None = None,
        _request_id: str | None = None,
        pipeline_run_id: uuid.UUID | None = None,
        request_id: uuid.UUID | None = None,
        org_id: uuid.UUID | None = None,
        interaction_id: uuid.UUID | None = None,
        topology: str = "chat_fast",
        skills_context: list[SkillContextForLLM] | None = None,
        model_id: str | None = None,
        platform: str | None = None,
        behavior: str | None = None,
        skill_ids: list[str] | None = None,
        send_status: Callable | None = None,
        send_token: Callable | None = None,
    ) -> tuple[str, uuid.UUID]:
        """Handle an incoming chat message using the DAG orchestrator.

        This method uses the StageGraph-based approach with agent routing
        for topology/behavior selection.

        Args:
            content: User message content
            session_id: Session identifier
            user_id: User identifier
            message_id: Optional client-generated message ID
            assistant_message_id: Optional assistant message ID
            pipeline_run_id: Optional pipeline run ID for observability
            request_id: Optional request ID for tracing
            org_id: Optional organization ID
            interaction_id: Optional interaction ID
            topology: Pipeline topology (e.g., "chat_fast", "chat_accurate")
            skills_context: Pre-computed skills context
            model_id: Optional LLM model override
            platform: Client platform (web, native, etc.)
            behavior: High-level behavior label (e.g., "practice", "roleplay")
            skill_ids: Optional list of skill IDs to practice
            send_status: Status callback
            send_token: Token callback

        Returns:
            Tuple of (full response content, assistant message ID)
        """
        from app.ai.substrate.stages.pipeline_registry import pipeline_registry

        # Generate message IDs if not provided
        if message_id is None:
            if pipeline_run_id is not None:
                message_id = uuid.uuid5(pipeline_run_id, "user")
            else:
                message_id = uuid.uuid4()
        if assistant_message_id is None:
            if pipeline_run_id is not None:
                assistant_message_id = uuid.uuid5(pipeline_run_id, "assistant")
            else:
                assistant_message_id = uuid.uuid4()

        # Record start time for metrics
        start_time = time.time()

        # Create pipeline context - topology is now directly provided
        pipeline_ctx = PipelineContext(
            pipeline_run_id=pipeline_run_id,
            request_id=request_id,
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            interaction_id=interaction_id,
            topology=topology,
            configuration={},
            behavior=behavior,
            service="chat",
            event_sink=get_event_sink(),
            data={},
            db=self.db,
        )

        # Initialize context data
        pipeline_ctx.data.update(
            {
                "text": content,
                "topology": topology,
                "behavior": behavior,
                "skill_ids": skill_ids,
                "message_id": message_id,
                "assistant_message_id": assistant_message_id,
                "send_status": send_status,
                "send_token": send_token,
                "platform": platform,
                "model_id": model_id,
                "skills_context": skills_context,
                "input_type": "typed",
            }
        )

        # Use topology directly (no more quality_mode -> topology mapping needed)
        pipeline_name = topology

        # Create ports dict directly (avoid asdict() which deepcopies and fails on modules)

        # Create pipeline from registry
        pipeline = pipeline_registry.get(pipeline_name)
        graph = pipeline.build()

        # Run via Kernel orchestrator for lifecycle management
        orchestrator = PipelineOrchestrator()

        async def _runner(send_status_cb, send_token_cb):
            # Inject wrapped callbacks into context
            pipeline_ctx.data["send_status"] = send_status_cb
            pipeline_ctx.data["send_token"] = send_token_cb

            # Add stage dependencies for injection
            pipeline_ctx.data.update({
                "llm_provider": self._chat_service.llm,
                "chat_service": self._chat_service,
                "db": self.db,
                "call_logger": None,  # Created on-demand if needed
                "retry_fn": lambda fn, *args, **kwargs: fn(*args, **kwargs),  # Simple passthrough
            })

            # Create snapshot for stage context
            snapshot = ContextSnapshot(
                pipeline_run_id=pipeline_ctx.pipeline_run_id,
                request_id=pipeline_ctx.request_id,
                session_id=pipeline_ctx.session_id,
                user_id=pipeline_ctx.user_id,
                org_id=pipeline_ctx.org_id,
                interaction_id=pipeline_ctx.interaction_id,
                topology=pipeline_ctx.topology,
                channel="chat_channel",
                behavior=pipeline_ctx.behavior,
                input_text=pipeline_ctx.data.get("text", ""),
                messages=[],
            )

            # Create ports and inputs for stage context
            ports = create_stage_ports(
                db=self.db,
                send_status=send_status_cb,
                send_token=send_token_cb,
                chat_service=self._chat_service,
            )

            inputs = create_stage_inputs(
                snapshot=snapshot,
                ports=ports,
            )

            # Create stage context with data for dependency injection
            stage_ctx = create_stage_context(
                snapshot=snapshot,
                config={"inputs": inputs, "data": dict(pipeline_ctx.data)},
            )

            await graph.run(stage_ctx)
            return {
                "success": True,
                "agent_id": pipeline_ctx.data.get("agent_id"),
            }

        try:
            await orchestrator.run(
                pipeline_run_id=pipeline_run_id or uuid.uuid4(),
                service="chat",
                topology=pipeline_name,
                behavior=pipeline_ctx.behavior,
                trigger="typed_input",
                request_id=request_id or uuid.uuid4(),
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                send_status=send_status or (lambda *_args, **_kw: asyncio.sleep(0)),
                send_token=send_token or (lambda *_args, **_kw: asyncio.sleep(0)),
                runner=_runner,
            )
        except StageExecutionError as exc:
            logger.error(
                "Chat pipeline stage failed",
                extra={
                    "service": "chat",
                    "stage": exc.stage,
                    "error": str(exc),
                    "session_id": str(session_id),
                    "user_id": str(user_id),
                },
            )
            raise

        # Extract results
        llm_output = pipeline_ctx.data.get("llm_output")
        persist_output = pipeline_ctx.data.get("persist_output")

        # Persist pipeline run metrics for observability
        duration_ms = int((time.time() - start_time) * 1000)

        # Rough token estimates
        estimated_tokens_in = len(content) // 4
        token_count = int(getattr(llm_output, "tokens", 0) or 0)

        if pipeline_run_id is not None:
            from app.database import get_session_context
            from app.models.observability import PipelineRun

            async with get_session_context() as obs_db:
                run = await obs_db.get(PipelineRun, pipeline_run_id)
                if run is not None:
                    ttft_ms_value = getattr(llm_output, "ttft_ms", None)
                    if ttft_ms_value is not None:
                        run.ttft_ms = ttft_ms_value

                    run.tokens_in = estimated_tokens_in
                    run.tokens_out = token_count
                    run.total_latency_ms = duration_ms

                    run_metadata = run.run_metadata or {}
                    run_metadata["quality_mode"] = extract_quality_mode(pipeline_ctx.topology)
                    run.run_metadata = run_metadata

                    stages = run.stages or {}
                    llm_stage = stages.get("llm") or {}
                    llm_stage.update(
                        {
                            "provider": getattr(llm_output, "provider", None),
                            "model": getattr(llm_output, "model", None),
                            "ttft_ms": ttft_ms_value,
                            "stream_token_count": token_count,
                        }
                    )
                    stages["llm"] = llm_stage
                    run.stages = stages
                    obs_db.add(run)

        return llm_output.full_text, persist_output.assistant_message_id

    async def build_pipeline_context(
        self,
        session_id: uuid.UUID,
        _content: str,
        skills_context: list[SkillContextForLLM] | None = None,
        platform: str | None = None,
        precomputed_assessment=None,
        pipeline_run_id: uuid.UUID | None = None,
        request_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        org_id: uuid.UUID | None = None,
    ) -> ChatContext:
        """Build chat context using the ChatService.

        Delegates to ChatService for core context building.
        """
        return await self._chat_service.build_context(
            session_id=session_id,
            skills_context=skills_context,
            platform=platform,
            precomputed_assessment=precomputed_assessment,
            pipeline_run_id=pipeline_run_id,
            request_id=request_id,
            user_id=user_id,
            org_id=org_id,
        )
