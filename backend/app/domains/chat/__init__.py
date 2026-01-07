"""Chat domain - handles text conversations with LLM.

Services:
    - ChatService: Core chat operations (context building, persistence, LLM streaming)
    - ChatPipelineService: DAG/pipeline orchestration for chat messages

Specialized Services (SRP-compliant):
    - ChatPersistenceService: Database persistence for interactions and sessions
    - ChatContextService: Building LLM context from enrichers and history
    - ChatStreamingService: LLM streaming with fallback and circuit breaker
"""

from app.domains.chat.pipeline_service import ChatPipelineService
from app.domains.chat.service import ChatService
from app.domains.chat.services import (
    ChatContextService,
    ChatPersistenceService,
    ChatStreamingService,
)

__all__ = [
    "ChatService",
    "ChatPipelineService",
    "ChatPersistenceService",
    "ChatContextService",
    "ChatStreamingService",
]
